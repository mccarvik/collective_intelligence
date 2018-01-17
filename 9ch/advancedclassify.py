import pdb, sys
sys.path.append("/home/ubuntu/workspace/collective_intelligence")
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from pylab import *

yahookey="YOUR API KEY"
from xml.dom.minidom import parseString
from urllib import urlopen,quote_plus

loc_cache={}


class matchrow:
  def __init__(self,row,allnum=False):
    if allnum:
      self.data=[float(row[i]) for i in range(len(row)-1)]
    else:
      self.data=row[0:len(row)-1]
    self.match=int(row[len(row)-1])


def loadmatch(f,allnum=False):
  rows=[]
  for line in file(f):
    rows.append(matchrow(line.split(','),allnum))
  return rows
 

def plotagematches(rows):
  xdm,ydm=[r.data[0] for r in rows if r.match==1],\
          [r.data[1] for r in rows if r.match==1]
  xdn,ydn=[r.data[0] for r in rows if r.match==0],\
          [r.data[1] for r in rows if r.match==0] 
  
  plot(xdm,ydm,'bo')
  plot(xdn,ydn,'b+')
  plt.savefig('/home/ubuntu/workspace/collective_intelligence/9ch/age_matches.jpg')
  plt.close()


# Calculates the average data point for each possible result
def lineartrain(rows):
  averages={}
  counts={}
  
  for row in rows:
    # Get the class of this point
    cl=row.match
    
    averages.setdefault(cl,[0.0]*(len(row.data)))
    counts.setdefault(cl,0)
    
    # Add this point to the averages
    for i in range(len(row.data)):
      averages[cl][i]+=float(row.data[i])
      
    # Keep track of how many points in each class
    counts[cl]+=1
    
  # Divide sums by counts to get the averages
  for cl,avg in averages.items():
    for i in range(len(avg)):
      avg[i]/=counts[cl]
  
  return averages


def dotproduct(v1,v2):
  return sum([v1[i]*v2[i] for i in range(len(v1))])


def veclength(v):
  return sum([p**2 for p in v])


def dpclassify(point,avgs):
  # dot product will identify the angle between point to be classified and vector between the 2 averages
  # angle will dictate what side of the line separating the averages the point falls on
  b=(dotproduct(avgs[1],avgs[1]) - dotproduct(avgs[0],avgs[0]))/2
  y=dotproduct(point,avgs[0]) - dotproduct(point,avgs[1]) + b
  if y>0: return 0
  else: return 1


def yesno(v):
  if v=='yes': return 1
  elif v=='no': return -1
  else: return 0

  
def matchcount(interest1,interest2):
  l1=interest1.split(':')
  l2=interest2.split(':')
  x=0
  for v in l1:
    if v in l2: x+=1
  return x


def getlocation(address):
  if address in loc_cache: return loc_cache[address]
  #   data=urlopen('http://api.local.yahoo.com/MapsService/V1/'+\
  #               'geocode?appid=%s&location=%s' %
  #               (yahookey,quote_plus(address))).read()
  data=urlopen('http://local.yahooapis.com/MapsService/V1/geocode?appid=%s&location=%s' % (yahookey,quote_plus(address))).read()
  doc=parseString(data)
  lat=doc.getElementsByTagName('Latitude')[0].firstChild.nodeValue
  long=doc.getElementsByTagName('Longitude')[0].firstChild.nodeValue  
  loc_cache[address]=(float(lat),float(long))
  return loc_cache[address]


def milesdistance(a1,a2):
  return 0
  lat1,long1=getlocation(a1)
  lat2,long2=getlocation(a2)
  latdif=69.1*(lat2-lat1)
  longdif=53.0*(long2-long1)
  return (latdif**2+longdif**2)**.5


def loadnumerical():
  oldrows=loadmatch('matchmaker.csv')
  newrows=[]
  for row in oldrows:
    d=row.data
    data=[float(d[0]),yesno(d[1]),yesno(d[2]),
          float(d[5]),yesno(d[6]),yesno(d[7]),
          matchcount(d[3],d[8]),
          milesdistance(d[4],d[9]),
          row.match]
    newrows.append(matchrow(data))
  return newrows


def scaledata(rows):
  low=[999999999.0]*len(rows[0].data)
  high=[-999999999.0]*len(rows[0].data)
  # Find the lowest and highest values
  for row in rows:
    d=row.data
    for i in range(len(d)):
      if d[i]<low[i]: low[i]=d[i]
      if d[i]>high[i]: high[i]=d[i]
  
  # Create a function that scales data
  def scaleinput(d):
     return [(d[i]-low[i])/(high[i]-low[i]) for i in range(len(low)-1)]
  
  # Scale all the data
  newrows=[matchrow(scaleinput(row.data)+[row.match]) for row in rows]
  
  # Return the new data and the function
  return newrows,scaleinput


# Function used in place of dotproduct to transform data from more complex spaces
# Function helps to make more complex data sets linearly seperaple, ex: half moons / inner circles
# TODO: why is the rbf helpful?
def rbf(v1,v2,gamma=10):
  dv=[v1[i]-v2[i] for i in range(len(v1))]
  l=veclength(dv)
  return math.e**(-gamma*l)


def nlclassify(point,rows,offset,gamma=10):
  sum0=0.0
  sum1=0.0
  count0=0
  count1=0
  
  for row in rows:
    if row.match==0:
      sum0+=rbf(point,row.data,gamma)
      count0+=1
    else:
      sum1+=rbf(point,row.data,gamma)
      count1+=1
  
  # exact same process as the dotproduct but using different function (rbf)
  y=(1.0/count0)*sum0-(1.0/count1)*sum1+offset

  if y>0: return 0
  else: return 1

# offset is the same parameter as "b" calculated in dpclassify but using rbf_radial instead of dot product
def getoffset(rows,gamma=10):
  l0=[]
  l1=[]
  for row in rows:
    if row.match==0: l0.append(row.data)
    else: l1.append(row.data)
  # takes a while to run as the values arent averaged like for the dotproduct offset calc so have to run thru each row
  sum0=sum(sum([rbf(v1,v2,gamma) for v1 in l0]) for v2 in l0)
  sum1=sum(sum([rbf(v1,v2,gamma) for v1 in l1]) for v2 in l1)
  
  # pseudo averaging process of the sums
  return (1.0/(len(l1)**2))*sum1-(1.0/(len(l0)**2))*sum0


if __name__ == "__main__":
    agesonly = loadmatch('agesonly.csv', allnum=True)
    matchmaker = loadmatch('matchmaker.csv')
    # plotagematches(agesonly)
    
    # Linear Classifier
    # avgs = lineartrain(agesonly)
    # print(dpclassify([30,30], avgs))
    # print(dpclassify([30,25], avgs))
    # print(dpclassify([25,40], avgs))
    # print(dpclassify([48,20], avgs))
    
    # print(getlocation('1 alewife center, cambridge, ma'))
    # print(milesdistance('cambridge, ma', 'new york, ny'))
    
    numericalset = loadnumerical()
    # print(numericalset[0].data)
    scaledset, scalef = scaledata(numericalset)
    avgs = lineartrain(scaledset)
    # print(numericalset[0].data)
    # print(numericalset[0].match)
    # print(dpclassify(scalef(numericalset[0].data), avgs))
    # print(numericalset[11].match)
    # print(dpclassify(scalef(numericalset[11].data), avgs))

    # Kernel Stuff - nonlinear data
    # Just ages
    offset = getoffset(agesonly)
    print(nlclassify([30,30], agesonly, offset))
    print(nlclassify([30,25], agesonly, offset))
    print(nlclassify([25,40], agesonly, offset))
    print(nlclassify([48,20], agesonly, offset))
    
    # Using all the data
    pdb.set_trace()
    ssoffset = getoffset(scaledset)
    print(numericalset[0].match)
    print(nlclassify(scalef(numericalset[0].data), scaledset, ssoffset))
    print(numericalset[1].match)
    print(nlclassify(scalef(numericalset[1].data), scaledset, ssoffset))
    print(numericalset[2].match)
    print(nlclassify(scalef(numericalset[2].data), scaledset, ssoffset))
    newrow = [28.0, -1, -1, 26.0, -1, 1, 2, 0.8]  # Man doesn't want children, woman does
    print(nlclassify(scalef(newrow), scaledset, ssoffset))
    newrow = [28.0, -1, 1, 26.0, -1, 1, 2, 0.8]  # Both want children
    print(nlclassify(scalef(newrow), scaledset, ssoffset))
    