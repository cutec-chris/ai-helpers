import aiohttp,asyncio,bs4,logging

async def search(query, url=None):
    """
    Perform a web search using Searx and return a list of JSON objects.

    :param query: The search query as a string
    :param api_url: The URL of the Searx API
    :return: A list of JSON objects representing the search results
    """
    if url == None: url = "https://priv.au"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    }
    async def fetch_css_file(session, url):
        if not 'client' in url: return None
        async with session.get(url,headers=headers) as response:
            return await response.text()
    async with aiohttp.ClientSession() as session:
        params = {"q": query}
        logging.debug('searx:'+str(query))
        async with session.get(url+'/search', params=params,headers=headers) as response:
            response.raise_for_status()  # If the response is not successful, raise an exception
            html = await response.text()
            soup = bs4.BeautifulSoup(html, "html.parser")
            css_urls = [link.get("href") for link in soup.find_all("link", rel="stylesheet")]
            tasks = [fetch_css_file(session, url+'/'+file) for file in css_urls]
            results = []
            for result in soup.find_all("article", class_="result"):
                title = result.text.strip()
                url = result.find("a")["href"]
                try:
                    engines = result.find('div').text.strip()
                except:
                    engines = None
                results.append({"title": title, "url": url, "engines": engines})
            css_files = await asyncio.gather(*tasks)
            logging.debug('searx: finished (%d)' % len(results))
            return results