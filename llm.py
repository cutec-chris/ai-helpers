import aiohttp,ipaddress,urllib.parse,logging,re,json,time,asyncio,base64
from . import wol
class model:
    def __init__(self,model,api,**kwargs) -> None:
        self.model = model
        self.api = api
        self.wol = kwargs.get('wol',None)
        self.kwargs = kwargs
        self.fingerprint = None
        if '/v1' in self.api:
            self.api = self.api[:self.api.find('/v1')]
    async def watchdog(self):
        await asyncio.sleep(30)
        await self.avalible()
    async def internal_query(self,input,history=[],images=[],url="/v1/chat/completions"):
        wd = asyncio.create_task(self.watchdog())
        headers = {"Content-Type": "application/json"}
        if self.kwargs.get('apikey'):
            headers["Authorization"] = f"Bearer {self.kwargs.get('apikey')}"
        start_time = time.time()
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=None)) as session:
            ajson = {
                "model": self.model,
                "stream": False,
                "messages": [{"role": "system", "content": self.system}]\
                           +history
                           +[{"role": "user", "content": input}]
            }
            if len(images)>0:
                ajson["messages"][-1]["images"] = images
            if self.fingerprint != 'fp_ollama':
                #convert to openai format if not ollama
                new_messages = []
                for message in ajson["messages"]:
                    if message["role"] == "user" and "images" in message:
                        content = []
                        if "content" in message:
                            content.append({"type": "text", "text": message["content"]})
                        if "images" in message:
                            for image in message["images"]:
                                base64_image = image  # assume the image is already base64 encoded
                                decoded_image = base64.b64decode(base64_image)
                                # Look for the MIME type in the decoded string
                                mime_type = None
                                if decoded_image.startswith(b"\xff\xd8\xff\xe0"):
                                    mime_type = "image/jpeg"
                                elif decoded_image.startswith(b"\x89\x50\x4e\x47"):
                                    mime_type = "image/png"
                                elif decoded_image.startswith(b"\x47\x49\x46\x38"):
                                    mime_type = "image/gif"
                                content.append({"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}})
                        new_messages.append({"role": "user", "content": content})
                    else:
                        new_messages.append(message)  # keep other message types unchanged
                ajson["messages"] = new_messages
            if self.kwargs.get('keep_alive',None):
                ajson['keep_alive'] = self.kwargs.get('keep_alive')
            logging.debug('llm [%s]: query: %s' % (self.model,input))
            async with session.post(self.api+url, headers=headers, json=ajson) as resp:
                response_json = await resp.json()
                if 'error' in response_json:
                    if not response_json['error']['type'] == 'invalid_request_error':
                        logging.warning(str(response_json['error']['message']))
                    else:
                        logging.warning(str(response_json['error']['message']))
                    wd.cancel()
                    return False
                if 'choices' in response_json:
                    res = response_json['choices'][0]['message']['content']
                else:
                    res = response_json['message']['content']
                logging.debug('llm [%s]: answer: %s\n time: %.2fs' % (self.model,res,time.time()-start_time))
                wd.cancel()
                return res
        wd.cancel()
        return None
    async def internal_embedding(self,input):
        return None
    async def query(self,input,history=[],images=[]):
        if not await self.avalible():
            logging.warning('llm [%s]: server seems to be unavalible' % (self.model))
            return None
        if self.fingerprint == 'fp_ollama':
            return await ollama_model.internal_query(self,input,history,images)
        else: 
            return await self.internal_query(input,history,images)
    async def avalible(self):
        async def check_status():
            headers = {"Content-Type": "application/json"}
            ajson = {
                "model": self.model,
                "stream": False,
                "messages": []
            }                
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(connect=1)) as session:
                try:
                    start = time.time()
                    async with session.post(self.api+"/v1/chat/completions",headers=headers, json=ajson) as resp:
                        r = await resp.json()
                        if time.time()-start > 0.3:
                            logging.debug('llm [%s]: model loaded' % (self.model))
                        if 'system_fingerprint' in r:
                            self.fingerprint = r['system_fingerprint']
                            return True
                        else:
                            return True
                    ajson = {
                        "name": self.model,
                    }                
                except BaseException as e:
                    pass
                try:
                    async with session.post(self.api+"/api/show",headers=headers, json=ajson) as resp:
                        r = await resp.json()
                        if resp.ok:
                            self.fingerprint = 'fp_ollama'
                            return True
                except BaseException as e: 
                    pass
            return False
        if self.wol:
            Status_ok = False
            for a in range(3):
                purl = urllib.parse.urlparse(self.api)
                net = ipaddress.IPv4Network(purl.hostname + '/' + '255.255.255.0', False)
                wol.WakeOnLan(self.wol,[str(net.broadcast_address)])
                for i in range(60):
                    if await check_status() == True:
                        if i>0:
                            logging.debug('llm [%s]:client waked up after %d seconds' % (self.model,i))
                        Status_ok = True
                        break
                if Status_ok: break
        return await check_status()
    async def embedding(self,input):
        if not await self.avalible():
            logging.warning('llm [%s]: server seems to be unavalible' % (self.model))
            return None
        if self.fingerprint == 'fp_ollama':
            return await ollama_model.internal_embedding(self,input)
        else: 
            return await self.internal_embedding(self,input)
    def extract_json(self,text):
        if str(text) != text:
            return None
        pattern = r'{[^}]*}'
        pattern_c = re.compile(r'//.*\n', re.DOTALL)
        match = re.search(pattern, text)
        if match:
            json_str = match.group()
            json_str_c = pattern_c.sub('', json_str)
            try:
                return json.loads(json_str_c)
            except json.JSONDecodeError:
                return None
        return None
class ollama_model(model):
    def __init__(self, model, api, **kwargs) -> None:
        pass
    async def internal_query(self, input, history=[], images=[], url="/api/chat"):
        return await self.internal_query(input,history,images,url)
    async def internal_embedding(self, input, url="/api/embeddings"):
        headers = {"Content-Type": "application/json"}
        if self.kwargs.get('apikey'):
            headers["Authorization"] = f"Bearer {self.kwargs.get('apikey')}"
        start_time = time.time()
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=None)) as session:
            ajson = {
                "model": self.model,
                "prompt": input,
            }
            if self.kwargs.get('keep_alive',None):
                ajson['keep_alive'] = self.kwargs.get('keep_alive')
            #logging.debug('llm [%s]: embedding query len: %d' % (self.model,len(input)))
            async with session.post(self.api+url, headers=headers, json=ajson) as resp:
                response_json = await resp.json()
                if 'error' in response_json:
                    logging.warning(str(response_json['error']))
                    return False
                res = response_json['embedding']
                logging.debug('llm [%s]: embedding len %d done in %.2fs' % (self.model,len(input),time.time()-start_time))
                return res
