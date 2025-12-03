import busunAgent
import javbusAgent
import javdbAgent
import dmmAgent
import javlibAgent
import caribAgent
import javtrailers
#import manualAdd
import re
import ssl
from SSLEXTRA import sslOptions
import inspect


# URLS

def Start():
    HTTP.CacheTime = CACHE_1MINUTE
    HTTP.Headers['User-Agent'] = 'Plex Media Server/%s' % Platform.ServerVersion
    HTTP.Headers['Cookie'] = 'cok=1'

class OneJavAgent(Agent.Movies):
    name = 'onejav'
    languages = [Locale.Language.English,  Locale.Language.Japanese,  Locale.Language.Chinese]
    primary_provider = True
    accepts_from = ['com.plexapp.agents.localmedia']
    
    
    def search(self, results, media, lang, manual):
        Log('media.name :%s' % media.name)
        manualK = re.compile(r'^add ')
        if manualK.search(media.name) is not None:
            Log('Manual adding')
            #manualAdd.search(media.name,results,media)
            return
        file_name = media.name.strip().replace(' ', '-')
        file_name = re.sub('([A-z]-?)00(\d\d\d)',r'\1\2',file_name)

        code_match_pattern1 = '[a-zA-Z]{2,5}[-_][0-9]{3,5}'
        code_match_pattern2 = '([a-zA-Z]{2,5})([0-9]{3,5})'
        
        re_rules1 = re.compile(code_match_pattern1, flags=re.IGNORECASE)
        re_rules2 = re.compile(code_match_pattern2, flags=re.IGNORECASE)
        
        file_code1 = re_rules1.findall(file_name)
        file_code2 = re_rules2.findall(file_name)
        
        if file_code1:
            query = file_code1[0].upper()
        elif file_code2:
            query = file_code2[0][0].upper() + '-' + file_code2[0][1]
        else:
            query = file_name

        Log('query keyword :%s' % query)
  
        javtrailers.search(query,results,media,lang)
        javbusAgent.search(query,results,media,lang)
        #javdbAgent.search(query,results,media,lang)
        javlibAgent.search(query,results,media,lang)

        uncen_match_pattern = '[0-9]{6}[-_][0-9]{3}'
        re_rules_uncen = re.compile(uncen_match_pattern, flags=re.IGNORECASE)
        Uncen = ['carib','1pon','heyzo','uncen']
        uncen_matched = 0
        for x in Uncen:
            if query.find(x) >= 0:
                uncen_matched = 1
        if re_rules_uncen.findall(query) or uncen_matched:
            busunAgent.search(query,results,media,lang)
            import caribAgent
            caribAgent.search(query,results,media,lang)

        #try:
        #    import imageCrop
        #    imageCrop.crop23("https://pics.dmm.co.jp/mono/movie/adult/zocm035/zocm035pl.jpg")
        #except Exception as e:
        #    raise
        #    Log("An error occured when loading data: " + str(e))
        

    def update(self, metadata, media, lang): 
        Log(metadata.id)
        self.id = str(metadata.id).split("|")[0]
        if self.id == "carib":
            caribAgent.update(metadata,media,lang)
        javtrailers.update(metadata,media,lang)
        javlibAgent.update(metadata,media,lang)
        javbusAgent.update(metadata,media,lang)
        #javdbAgent.update(metadata,media,lang)
        #dmmAgent.update(metadata,media,lang)        
        
        try:
            if len(metadata.roles) == 0:
                #Log(metadata.roles)
                metadata.genres.add('No_Name')
            subbed = re.search('(\d-[cC]\W)|(\dch\W)|(\d-UC\W)',str(metadata.id).split("|")[2])
            if subbed:
                metadata.genres.add("中字")
                metadata.collections.add("中字")
            uhd = re.search('(4k|2160p)', str(metadata.id).split("|")[2], flags=re.IGNORECASE)
            if uhd:
                Log("Found 4K video")
                metadata.title_sort = metadata.title
                metadata.title = "[4K]" + metadata.title
            #metadata.collections.add("4K")

        except Exception as e:
            raise
            Log("An error occured when getting sub status: " + str(e))
        
        try:
            from gfriends import gfriends
            for role in metadata.roles:
                if role.photo == None:
                    roleImg = gfriends.get(role.name.upper(), "")
                #if roleImg.split("jpg")[1] is not None:
                #    roleImg = "%s%s"%(roleImg.split(".jpg")[0],".jpg")
                    Log(roleImg)
                    role.photo = roleImg
            return
        except Exception as e:
            raise
            Log("An error occured when loading data: " + str(e))

