import bs4,aiohttp,markdownify,logging,asyncio,time
async def download(url,Timeout=5):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
#        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    }
    logging.debug('scrape:downloading [%s]' % str(url))
    def convert_html(html):
        soup = bs4.BeautifulSoup(html, "html.parser")
        res = markdownify.MarkdownConverter().convert_soup(soup)
        return res
    try:
        loop = asyncio.get_running_loop()
        start_time = time.time()
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=Timeout)) as session:
            async with session.get(url,headers=headers) as response:
                response.raise_for_status()  # If the response is not successful, raise an exception
                html = await response.text()
                logging.debug('scrape:converting [%s] time: %.2fs' % (str(url),time.time()-start_time))
                res = await loop.run_in_executor(None, convert_html, html)
                logging.debug('scrape:finished [%s] time: %.2fs' % (str(url),time.time()-start_time))
                return res
    except BaseException as e:
        logging.warning('scrape: error [%s]: %s' % (str(url),str(e)))
        return None