import aiohttp,ipaddress,urllib.parse,logging,re,json,time,asyncio
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
    async def internal_query(self,input,history=[],images=[],url="/v1/chat/completions"):
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
            if self.kwargs.get('keep_alive',None):
                ajson['keep_alive'] = self.kwargs.get('keep_alive')
            logging.debug('llm [%s]: query: %s' % (self.model,input))
            async with session.post(self.api+url, headers=headers, json=ajson) as resp:
                response_json = await resp.json()
                if 'error' in response_json:
                    if not response_json['error']['type'] == 'invalid_request_error':
                        logging.warning(str(response_json['error']['message']))
                        return False
                if 'choices' in response_json:
                    res = response_json['choices'][0]['message']['content']
                else:
                    res = response_json['message']['content']
                logging.debug('llm [%s]: answer: %s\n time: %.2fs' % (self.model,res,time.time()-start_time))
                return res
        return None
    async def query(self,input,history=[],images=[]):
        if not await self.avalible():
            logging.warning('llm [%s]: server seems to be unavalible' % (self.model))
            return None
        if self.fingerprint == 'fp_ollama':
            return await ollama_model.internal_query(self,input,history,images)
        else: 
            return await self.internal_query(self,input,history,images)
    async def avalible(self):
        async def check_status():
            try:
                headers = {"Content-Type": "application/json"}
                ajson = {
                    "model": self.model,
                    "stream": False,
                    "messages": [{"role": "system", "content": ""}]\
                               +[{"role": "user"  , "content": ""}]
                }                
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(connect=1)) as session:
                    start = time.time()
                    async with session.post(self.api+"/v1/chat/completions",headers=headers, json=ajson) as resp:
                        r = await resp.json()
                        if time.time()-start > 0.1:
                            logging.debug('llm [%s]: model loaded' % (self.model))
                        self.fingerprint = r['system_fingerprint']
                        return True
            except BaseException as e: 
                logging.warning(str(e))
            return False
        if self.wol:
            Status_ok = False
            for a in range(3):
                purl = urllib.parse.urlparse(self.api)
                net = ipaddress.IPv4Network(purl.hostname + '/' + '255.255.255.0', False)
                wol.WakeOnLan(self.wol,[str(net.broadcast_address)])
                for i in range(60):
                    if await check_status() == True:
                        logging.debug('llm [%s]:client waked up after %d seconds' % (self.model,i))
                        Status_ok = True
                        break
                if Status_ok: break
        return await check_status()
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