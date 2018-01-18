import httplib, pdb
from xml.dom.minidom import parse, parseString, Node
import numpredict

devKey = 'af8779e0-45c5-4561-81c1-d0a3b3414136'
appKey = 'KevinMcC-mccarvik-PRD-55d7504c4-35ec43f9'
certKey = 'PRD-5d7504c44b9f-25db-4f2b-b352-f6f0'
serverUrl = 'api.ebay.com'
userToken = 'AgAAAA**AQAAAA**aAAAAA**pQpZWg**nY+sHZ2PrBmdj6wVnY+sEZ2PrA2dj6AFlYChDpCGpg+dj6x9nY+seQ**lhgEAA**AAMAAA**tpjHCI2yUDx0EArpI+NYhPypd9iJDV7SLMAsbwGxgn1yQpGrci1fNWt2+JeF+ggAh/ODHIfj71A855rx6jVAtsX553GC/fklV13YEx5wuae3TvHewqdwNgwqBtUfnwX8xP+8I1isU7aqcAiFeeIgHcX1U4G87sXrxfb7GI4QBSZ6dMCmEMsoXeK4tua1AF5I7tuvUSoQytiwfNdlq/z1EN66SR8s7XbFKgfPzuNB9mhPngL3aAXGnM0QrTRhI00khsH0WKGFvZ1tMLPJXCQMpXtHExnr3AjO1iQu+KJAHg0UKorGvdoNHyqTP7AA00hDDfo2czQVoROluxkBPB0WJBiIbBgdKQM24fppLCUbnULCLfNq/kiIofEyg1/i2jYFk4E4frAFYhQnMYFaC7C4evZ8lQ72tNG95UscCtWuJdSUInKM+ecdKXmKHF3qmcFzFgpU+CsaXHd/LRAuB0UgwPe8cR+qJtE2t+nkZ8PwJSHfNVjfvBiRlBIVIINMGAtOXdh/hvfr+gJf2EGBlSvsiSnr8DiBD4i4rfgoLEapsMMs3kYZxT1bK/wDnbP+xdHE61BU8YPLLTCfyYCf6tCoZUSIz4RVeaZy3TTbzE1Is6jUXQyfmCIsTiarw6jqFkPIZyu4PzfhIItoC+C6hIG2JtWq9cOuGUEHPOCkh0gKNYibfI5/yxCvzGSIVgODYceblzWO1LFsHLLbH7Dm//k9gQ/hNCQakuuOITtjRH/Q0/5mtCvbp55Ww/ZOELlUnJC6'

def getHeaders(apicall,siteID="0",compatabilityLevel = "433"):
  headers = {"X-EBAY-API-COMPATIBILITY-LEVEL": compatabilityLevel,	
             "X-EBAY-API-DEV-NAME": devKey,
             "X-EBAY-API-APP-NAME": appKey,
             "X-EBAY-API-CERT-NAME": certKey,
             "X-EBAY-API-CALL-NAME": apicall,
             "X-EBAY-API-SITEID": siteID,
             "Content-Type": "text/xml"}
  return headers


def sendRequest(apicall,xmlparameters):
  connection = httplib.HTTPSConnection(serverUrl)
  connection.request("POST", '/ws/api.dll', xmlparameters, getHeaders(apicall))
  response = connection.getresponse()
  if response.status != 200:
    print "Error sending request:" + response.reason
  else: 
    data = response.read()
    connection.close()
  return data


def getSingleValue(node,tag):
  nl=node.getElementsByTagName(tag)
  if len(nl)>0:
    tagNode=nl[0]
    if tagNode.hasChildNodes():
      return tagNode.firstChild.nodeValue
  return '-1'


def doSearch(query,categoryID=None,page=1):
  xml = "<?xml version='1.0' encoding='utf-8'?>"+\
        "<GetSearchResultsRequest xmlns=\"urn:ebay:apis:eBLBaseComponents\">"+\
        "<RequesterCredentials><eBayAuthToken>" +\
        userToken +\
        "</eBayAuthToken></RequesterCredentials>" + \
        "<Pagination>"+\
          "<EntriesPerPage>200</EntriesPerPage>"+\
          "<PageNumber>"+str(page)+"</PageNumber>"+\
        "</Pagination>"+\
        "<Query>" + query + "</Query>"
  if categoryID!=None:
    xml+="<CategoryID>"+str(categoryID)+"</CategoryID>"
  xml+="</GetSearchResultsRequest>"
  
  data=sendRequest('GetSearchResults',xml)
  response = parseString(data)
  itemNodes = response.getElementsByTagName('Item');
  results = []
  for item in itemNodes:
    itemId=getSingleValue(item,'ItemID')
    itemTitle=getSingleValue(item,'Title')
    itemPrice=getSingleValue(item,'CurrentPrice')
    itemEnds=getSingleValue(item,'EndTime')
    results.append((itemId,itemTitle,itemPrice,itemEnds))
  return results


def getCategory(query='',parentID=None,siteID='0'):
  lquery=query.lower()
  xml = "<?xml version='1.0' encoding='utf-8'?>"+\
        "<GetCategoriesRequest xmlns=\"urn:ebay:apis:eBLBaseComponents\">"+\
        "<RequesterCredentials><eBayAuthToken>" +\
        userToken +\
        "</eBayAuthToken></RequesterCredentials>"+\
        "<DetailLevel>ReturnAll</DetailLevel>"+\
        "<ViewAllNodes>true</ViewAllNodes>"+\
        "<CategorySiteID>"+siteID+"</CategorySiteID>"
  if parentID==None:
    xml+="<LevelLimit>1</LevelLimit>"
  else:
    xml+="<CategoryParent>"+str(parentID)+"</CategoryParent>"
  xml += "</GetCategoriesRequest>"
  data=sendRequest('GetCategories',xml)
  categoryList=parseString(data)
  catNodes=categoryList.getElementsByTagName('Category')
  for node in catNodes:
    catid=getSingleValue(node,'CategoryID')
    name=getSingleValue(node,'CategoryName')
    if name.lower().find(lquery)!=-1:
      print catid,name


def getItem(itemID):
  xml = "<?xml version='1.0' encoding='utf-8'?>"+\
        "<GetItemRequest xmlns=\"urn:ebay:apis:eBLBaseComponents\">"+\
        "<RequesterCredentials><eBayAuthToken>" +\
        userToken +\
        "</eBayAuthToken></RequesterCredentials>" + \
        "<ItemID>" + str(itemID) + "</ItemID>"+\
        "<DetailLevel>ItemReturnAttributes</DetailLevel>"+\
        "</GetItemRequest>"
  data=sendRequest('GetItem',xml)
  result={}
  response=parseString(data)
  result['title']=getSingleValue(response,'Title')
  sellingStatusNode = response.getElementsByTagName('SellingStatus')[0];
  result['price']=getSingleValue(sellingStatusNode,'CurrentPrice')
  result['bids']=getSingleValue(sellingStatusNode,'BidCount')
  seller = response.getElementsByTagName('Seller')
  result['feedback'] = getSingleValue(seller[0],'FeedbackScore')

  attributeSet=response.getElementsByTagName('Attribute');
  attributes={}
  for att in attributeSet:
    attID=att.attributes.getNamedItem('attributeID').nodeValue
    attValue=getSingleValue(att,'ValueLiteral')
    attributes[attID]=attValue
  result['attributes']=attributes
  return result


def makeLaptopDataset():
  searchResults=doSearch('laptop',categoryID=51148)
  result=[]
  for r in searchResults:
    item=getItem(r[0])
    att=item['attributes']
    try:
      data=(float(att['12']),float(att['26444']),
            float(att['26446']),float(att['25710']),
            float(item['feedback'])
           )
      entry={'input':data,'result':float(item['price'])}
      result.append(entry)
    except:
      print item['title']+' failed'
  return result
  
  
if __name__ == '__main__':
  laptops = doSearch('laptop')
  print(laptops[0:10])
  
  getCategory('computers')
  getCategory('laptops', parentID=58058)
  laptops = doSearch('laptop', categoryID=51148)
  print(laptops[0:10])
  # getItem(laptops[7][10])
  set1 = makeLaptopDataset()
  # numpredict.knnestimate(set1, (512, 1000, 14, 40, 1000))
  # numpredict.knnestimate(set1, (1024, 1000, 14, 40, 1000))
  # numpredict.knnestimate(set1, (1024, 1000, 14, 60, 0))
  # numpredict.knnestimate(set1, (1024, 2000, 14, 60, 1000))