import requests
from bs4 import BeautifulSoup
import os
import logging
from flask import Flask, render_template, request, send_from_directory
import certifi
import zipfile
import shutil
import pymongo

logging.basicConfig(filename="scrapper.log", level=logging.INFO)

app = Flask(__name__)

@app.route("/", methods=['GET'])
def homepage():
    return render_template("index.html")

@app.route("/download", methods=['POST'])
def index():
    try:
        if request.method == 'POST':
            # query to search for images
            query = request.form['content'].replace(" ", "")

            # directory to save the scraped data
            save_dir = "images/"
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
            }

            response = requests.get(f"https://www.google.com/search?sca_esv={query}&sxsrf=ACQVn08pBMV6T4ZChaOQuIt9S9vWL0FG8A:1705806780893&q=cat&tbm=isch&source=lnms&sa=X&ved=2ahUKEwj02uu5we2DAxVI8jgGHQmUCAsQ0pQJegQIEBAB&biw=1200&bih=693&dpr=2")

            soup = BeautifulSoup(response.content, 'html.parser')
            images_tags = soup.find_all("img")
            del images_tags[0]

            img_data_mongo = []
            for index, img_tag in enumerate(images_tags):
                image_url = img_tag['src']
                try:
                    image_data = requests.get(image_url).content
                    image_filename = f"{query}_{index}.jpg"
                    image_path = os.path.join(save_dir, image_filename)
                    with open(image_path, "wb") as f:
                        f.write(image_data)
                    mydict = {"index": index, "image": image_path}
                    img_data_mongo.append(mydict)
                except Exception as e:
                    print(f"Error downloading image {index}: {e}")

            if img_data_mongo:
                # Create a zip file containing the downloaded images
                zip_filename = "scrapper_images.zip"
                with zipfile.ZipFile(zip_filename, 'w') as zip_file:
                    for img_dict in img_data_mongo:
                        image_path = img_dict["image"]
                        zip_file.write(image_path, os.path.basename(image_path))

                # Move the zip file to the static folder (make sure the folder exists)
                static_folder = "static/"
                if not os.path.exists(static_folder):
                    os.makedirs(static_folder)
                zip_path = os.path.join(static_folder, zip_filename)
                shutil.move(zip_filename, zip_path)

                return render_template("results.html", query=query)
             # MongoDB insertion only when images are successfully downloaded
            uri = "mongodb+srv://anirudh7371:phoenix2509@cluster0.nzme8dh.mongodb.net/?retryWrites=true&w=majority"
            client = pymongo.MongoClient(uri, tlsCAFile=certifi.where())
            try:
                client.admin.command('ping')
                logging.info("Pinged your deployment. You successfully connected to MongoDB!")
                db = client["image_scrapping"]
                col = db["scrapped_data"]
                col.insert_many(img_data_mongo)
            except Exception as e:
                logging.error(e)

    except Exception as e:
        logging.error(e)

    # Return something in case no images are downloaded
    return render_template("error.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0")