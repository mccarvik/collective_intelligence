import xml.dom.minidom
import urllib2, pdb
import treepredict

zwskey="X1-ZWz1g6wg3hu2h7_4dboj"

def getaddressdata(address,city):
  escad=address.replace(' ','+')
  url='http://www.zillow.com/webservice/GetDeepSearchResults.htm?'
  url+='zws-id=%s&address=%s&citystatezip=%s' % (zwskey,escad,city)
  doc=xml.dom.minidom.parseString(urllib2.urlopen(url).read())
  code=doc.getElementsByTagName('code')[0].firstChild.data
  if code!='0': return None
  if 1:
    zipcode=doc.getElementsByTagName('zipcode')[0].firstChild.data
    use=doc.getElementsByTagName('useCode')[0].firstChild.data
    try:
        year=doc.getElementsByTagName('yearBuilt')[0].firstChild.data
    except Exception as e:
        return None
    
    try:
        sqft=doc.getElementsByTagName('finishedSqFt')[0].firstChild.data
    except Exception as e:
        return None
    
    try:
        bath=doc.getElementsByTagName('bathrooms')[0].firstChild.data
    except Exception as e:
        return None
    
    try:
        bed=doc.getElementsByTagName('bedrooms')[0].firstChild.data
    except Exception as e:
        return None
        
    rooms=1 #doc.getElementsByTagName('totalRooms')[0].firstChild.data
    
    try:
        price=doc.getElementsByTagName('amount')[0].firstChild.data
    except:
        return None
  else:
    return None
       
  return (zipcode,use,int(year),float(bath),int(bed),int(rooms),price)

def getpricelist():
  l1=[]
  for line in file('addresslist.txt'):
    data=getaddressdata(line.strip(),'Cambridge,MA')
    if data:
        l1.append(data)
  return l1
 

if __name__ == '__main__':
    housedata = getpricelist()
    housetree = treepredict.buildtree(housedata, scoref=treepredict.variance)
    treepredict.drawtree(housetree, 'housetree.jpg')