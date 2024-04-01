import os
import openai
import time
import csv
from tqdm import tqdm

# Set your OpenAI API key
OPENAI_API_TOKEN = "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"
os.environ["OPENAI_API_KEY"] = OPENAI_API_TOKEN

# Initialize the OpenAI client
client = openai.OpenAI()

# Function to upload a file to OpenAI
def upload_file(file_path, purpose):
    with open(file_path, "rb") as file:
        response = client.files.create(file=file, purpose=purpose)
    return response.id

# Upload your files
internal_links_file_id = upload_file('cryptoimages.txt', 'assistants')
content_plan_file_id = upload_file('contentplan.csv', 'assistants')

# Create an Assistant
assistant = client.beta.assistants.create(
    name="Infoautoblogger",
    model="gpt-3.5-turbo-1106",
    instructions="Lees cryptoimages.txt. Elk artikel moet minimaal 3 brand images en links naar hun pillar page hebben. Als je zoekt naar de brand images zorg ervoor dat deze relevant zijn voor het specifieke artikel dat je aan het schrijven bent. Je moet ervoor zorgen dat de brand image links volledig en correct geschreven zijn. Elk artikel moet brand images en hun respectievelijke internal link hebben. Zorg voor minimaal 3 echte brand image URLs in het afgemaakte artikel. Kies alleen relevante pagina's. Verzin geen image links. Verzin nooit links of brand images. Gebruik geen bronnen of voetnoten. Je kiest altijd 5 strikt relevante brand images en internal links voor de artikelen. Je gebruikt geen bronnen in de outline, maar kiest gewoon 5 brand images die relevant zijn voor het artikel. Eerst lees je de bijgevoegde bestanden en begrijp ze compleet, en dan op basis daarvan maak je een gedetailleerde outline over het blog post topic, inclusief een maximum van 5 strikt relevante internal links en brand image links. Deze worden uiteindelijk gebruikt om een artikel te schrijven.",    tools=[{"type": "retrieval"}],
    file_ids=[internal_links_file_id, content_plan_file_id]
)

def wait_for_run_completion(thread_id, run_id, timeout=300):
    start_time = time.time()
    while time.time() - start_time < timeout:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        if run_status.status == 'completed':
            return run_status
        time.sleep(10)
    raise TimeoutError("Run did not complete within the specified timeout.")

def get_internal_links(thread_id, blog_post_idea):
    get_request = f"Lees internallinks.txt, kies 5 relevante pagina's, hun links en respectieve afbeeldingen, die relevant zijn voor {blog_post_idea}.."
    client.beta.threads.messages.create(thread_id=thread_id, role="user", content=get_request)
    get_request_run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=assistant.id)
    wait_for_run_completion(thread_id, get_request_run.id)
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    return next((m.content for m in messages.data if m.role == "assistant"), None)

print (get_internal_links)

def process_blog_post(thread_id, blog_post_idea):
    outline_request = f"Verzin geen internal links. Gebruik de brand images en internal links uit {get_internal_links} en gebruik ze om een outline te maken voor een artikel over {blog_post_idea} Gebruik in de outline geen bronnen of voetnoten, maar voeg alleen relevante brand images toe in een relevante sectie, en een relevante internal link in een relevante sectie. Het is niet nodig om veel bronnen te gebruiken, elke artikel moet minimaal 5 brand images en internal links hebben."
    client.beta.threads.messages.create(thread_id=thread_id, role="user", content=outline_request)
    outline_run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=assistant.id)
    wait_for_run_completion(thread_id, outline_run.id)
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    outline = next((m.content for m in messages.data if m.role == "assistant"), None)

    print(f"Outline for '{blog_post_idea}':\n{outline}\n")


    article = None
    if outline:
        article_request = f"Gebruik brugklas niveau Nederlands. Gebruik geen overdreven creatieve of gekke taal. Schrijf alsof je voor de Telegraaf of een andere grote krant schrijft. Geef alleen informatie. Schrijf niet als in een magazine. Gebruik eenvoudige taal. Verzin geen image links. Je schrijft vanuit een first person plural perspectief (dus ons/onze). Voeg een key takeaway table toe aan de bovenkant van het artikel, die de belangrijkste punten samenvat. Verzin nooit links of image links. Kies 5 internal links en 1 afbeelding die relevant zijn voor het artikel en schrijf dan een gedetaillerd artikel gebaseerd op de volgende outline: \n{outline}, maak ook een goede titel voor het artikel waarop mensen willen klikken, de titel moet ongeveer 60 karakters zijn. Neem de merkafbeeldingen en internal links naar andere hoofdpagina's op natuurlijke en relevante wijze op in het artikel.Gebruik markdown-formatting en zorg ervoor dat je tabellen en lijsten gebruikt om aan de opmaak toe te voegen. Gebruik 3 relevante brand images en hoofdpagina's met alleen internal links. Bedenk nooit interne links."
        client.beta.threads.messages.create(thread_id=thread_id, role="user", content=article_request)
        article_run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=assistant.id)
        wait_for_run_completion(thread_id, article_run.id)
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        article = next((m.content for m in messages.data if m.role == "assistant"), None)

        print(f"Article for '{blog_post_idea}':\n{article}\n")


    return outline, article

def process_content_plan():
    input_file = 'content_plan.csv'
    output_file = 'processed_content_plan.csv'
    processed_rows = []

    with open(input_file, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in tqdm(reader, desc="Processing Blog Posts"):
            if row.get('Processed', 'No') == 'Yes':
                continue

            blog_post_idea = row['Blog Post Ideas']
            thread_id = client.beta.threads.create().id  # New thread for each blog post
            outline, article = process_blog_post(thread_id, blog_post_idea)

            if outline and article:
                row.update({'Blog Outline': outline, 'Article': article, 'Processed': 'Yes'})
                processed_rows.append(row)

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=processed_rows[0].keys())
        writer.writeheader()
        writer.writerows(processed_rows)

# Example usage
process_content_plan()
