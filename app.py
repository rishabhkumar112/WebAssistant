from flask import Flask, render_template, request, redirect, flash
from googlesearch import search
from tqdm import tqdm
from bs4 import BeautifulSoup as bs
from urllib.parse import urljoin, urlparse
from textblob import TextBlob
from pyutil import filereplace
from notify_run import Notify
import bs4
import requests
import webbrowser
import time
import os

notify = Notify()
# uncomment this to register first
# notify.register()

app = Flask(__name__)
app.secret_key = "mysecret123"

# utility functions for image download section
def is_valid(url):
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)

def get_all_images(url):
    # this functions returns all the image urls on the single page
    soup = bs(requests.get(url).content, "html.parser")

    urls = []
    for img in tqdm(soup.find_all("img"), "Extracting Images"):
        img_url = img.attrs.get("src")

        if not img_url:
            # if the image does not have src attribute just skip
            continue

        img_url = urljoin(url, img_url)
        try:
            pos = img_url.index("?")
            img_url = img_url[:pos]

        except ValueError:
            pass

        if is_valid(img_url):
            urls.append(img_url)

    return urls

def download(url, pathname):
    # if path doesn't exists, make the path dir
    if not os.path.isdir(pathname):
        os.makedirs(pathname)

    # downloading the body of the response by chunk, not immediately
    response = requests.get(url, stream=True)

    # get the total file size
    file_size = int(response.headers.get("Content-Length", 0))

    # get the file name
    filename = os.path.join(pathname, url.split("/")[-1]) + '.png'

    # progress bar
    progress = tqdm(response.iter_content(
        1024), f"Downloading {filename}", total=file_size, unit="B", unit_scale=True, unit_divisor=1024)
    with open(filename, "wb") as f:
        for data in progress:
            # saving data
            f.write(data)
            # updating progress bar
            progress.update(len(data))

# utility section ends

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/youtube', methods=['POST', 'GET'])
def youtube():
    if (request.method == "POST"):
        video_name = request.form['video_name']
        song_str = video_name + " Now Playing"
        # adding "song youtube" in the search query for more accurate results
        video_name = video_name + " song Youtube"
        # fetching google search top result
        for link in search(video_name, tld="co.in", num=1, stop=1, pause=2):
            print(link)
            webbrowser.open(link)
    notify.send(song_str)
    return redirect('/')

@app.route('/news', methods=['POST', 'GET'])
def news():
    if (request.method == "POST"):
        topic = request.form['news_topic']

        # make api call
        url_news = "https://newsapi.org/v2/everything?"
        parameters = {
            'q': topic,
            'pagesize': 10,
            'sortby': 'date',
            'apikey': '4fb51426b6df47f19d0982b9080a1267'
        }
        response = requests.get(url_news, params=parameters)

        # store results in json
        articles = response.json()

        # fetch top 5 articles
        news = []
        for i in range(5):
            news.append([articles["articles"][i]["title"], articles["articles"]
                         [i]["description"], articles["articles"][i]["url"]])
    notify.send("News articles fetched")
    return render_template('/news.html', news=news, topic=topic)

@app.route('/product', methods=['POST', 'GET'])
def product():
    if(request.method == "POST"):
        product_name = request.form['product_name']

        # flipkart
        flipkart_url = "https://www.flipkart.com/search?q=" + product_name
        flipkart_page = requests.get(flipkart_url)
        flipkart_soup = bs4.BeautifulSoup(flipkart_page.text, 'html.parser')

        flipkart_price = flipkart_soup.find(
            'div', class_="_1vC4OE _2rQ-NK").text

        # ebay
        ebay_url = "https://www.ebay.com/sch/i.html?_from=R40&_trksid=m570.l1313&_nkw=" + product_name
        ebay_page = requests.get(ebay_url)
        ebay_soup = bs4.BeautifulSoup(ebay_page.text, 'html.parser')

        ebay_price = ebay_soup.find('span', class_="s-item__price").text

    return render_template('/product.html', product_name=product_name, flipkart_price=flipkart_price, ebay_price=ebay_price)

@app.route('/alarm', methods=['POST', 'GET'])
def alarm():
    if(request.method == "POST"):
        website_url = request.form['website_url']
        set_alarm = request.form['set_alarm']
        current_time = time.strftime("%I:%M:%S")

        while(current_time != set_alarm):
            current_time = time.strftime("%I:%M:%S")
            time.sleep(1)

        if(set_alarm == current_time):
            alarm_str = website_url + " opened in browser"
            notify.send(alarm_str)
            webbrowser.open(website_url)

    return redirect('/')

# can be used for fast spell check and correction for files
@app.route('/spellCheck', methods=['POST', 'GET'])
def spellCheck():
    if(request.method == 'POST'):
        print(request.form['file_name'])
        with open(request.form['file_name'], 'r+') as file:
            for line in file:
                for word in line.split():
                    crr = TextBlob(word)
                    print(str(crr.correct()))
                    filereplace("missepelled.txt", word, str(crr.correct()))

    notify.send("Hey all checked!, check your file")

    return redirect('/')

# can be used for data collection for image processing
# can be used to grab many wallpapers and check later
# It can be extended to music, ringtones, files etc
# https://www.gettyimages.in/photos/image?mediatype=photography&phrase=image&sort=mostpopular
@app.route('/imageDownload', methods=['POST', 'GET'])
def main():
    # get all images
    url = request.form['url_name']
    path = urlparse(url).netloc
    imgs = get_all_images(url)
    for img in imgs:
        download(img, path)

    notify.send('All Images download successfully!, check your files')

    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)