from pysqlite2 import dbapi2 as sqlite
import re, math, pdb
import feedfilter

def getwords(doc):
  splitter=re.compile('\\W*')
  # print(doc)
  # Split the words by non-alpha characters
  pdb.set_trace()
  words=[s.lower() for s in splitter.split(doc) if len(s)>2 and len(s)<20]
  
  # Return the unique set of words only
  return dict([(w,1) for w in words])

class classifier:
  def __init__(self, getfeatures, filename=None):
    # Counts of feature/category combinations
    self.fc={}
    # Counts of documents in each category
    self.cc={}
    self.getfeatures=getfeatures
    
  def setdb(self,dbfile):
    self.con=sqlite.connect(dbfile)  
    self.con.execute('drop table if exists fc')
    self.con.execute('drop table if exists cc')
    self.con.execute('create table if not exists fc(feature,category,count)')
    self.con.execute('create table if not exists cc(category,count)')

  def incf(self,f,cat):
    count=self.fcount(f,cat)
    if count==0:
      self.con.execute("insert into fc values ('%s','%s',1)" % (f,cat))
    else:
      self.con.execute("update fc set count=%d where feature='%s' and category='%s'" % (count+1,f,cat)) 
  
  def fcount(self,f,cat):
    res=self.con.execute(
      'select count from fc where feature="%s" and category="%s"' % (f,cat)).fetchone()
    if res==None: return 0
    else: return float(res[0])

  def incc(self,cat):
    count=self.catcount(cat)
    if count==0:
      self.con.execute("insert into cc values ('%s',1)" % (cat))
    else:
      self.con.execute("update cc set count=%d where category='%s'" % (count+1,cat))    

  def catcount(self,cat):
    res=self.con.execute('select count from cc where category="%s"' % (cat)).fetchone()
    if res==None: return 0
    else: return float(res[0])

  def categories(self):
    cur=self.con.execute('select category from cc');
    return [d[0] for d in cur]

  def totalcount(self):
    res=self.con.execute('select sum(count) from cc').fetchone();
    if res==None: return 0
    return res[0]

  def train(self,item,cat):
    features=self.getfeatures(item)
    # Increment the count for every feature with this category
    for f in features:
      self.incf(f,cat)

    # Increment the count for this category
    self.incc(cat)
    self.con.commit()

  # P(f|cat) --> probability of f, given cat
  def fprob(self,f,cat):
    if self.catcount(cat)==0: return 0

    # The total number of times this feature appeared in this 
    # category divided by the total number of items in this category
    return self.fcount(f,cat)/self.catcount(cat)

  def weightedprob(self,f,cat,prf,weight=1.0,ap=0.5):
    # Calculate current probability
    basicprob=prf(f,cat)

    # Count the number of times this feature has appeared in
    # all categories
    totals=sum([self.fcount(f,c) for c in self.categories()])

    # Calculate the weighted average
    bp=((weight*ap)+(totals*basicprob))/(weight+totals)
    return bp


class naivebayes(classifier):
  
  def __init__(self,getfeatures):
    classifier.__init__(self,getfeatures)
    self.thresholds={}
  
  def docprob(self,item,cat):
    features=self.getfeatures(item)   

    # Multiply the probabilities of all the features together
    p=1
    for f in features: p*=self.weightedprob(f,cat,self.fprob)
    return p

  def prob(self,item,cat):
    catprob=self.catcount(cat)/self.totalcount()
    docprob=self.docprob(item,cat)
    return docprob*catprob
  
  def setthreshold(self,cat,t):
    self.thresholds[cat]=t
    
  def getthreshold(self,cat):
    if cat not in self.thresholds: return 1.0
    return self.thresholds[cat]
  
  def classify(self,item,default=None):
    probs={}
    # Find the category with the highest probability
    max=0.0
    for cat in self.categories():
      probs[cat]=self.prob(item,cat)
      if probs[cat]>max: 
        max=probs[cat]
        best=cat

    # Make sure the probability exceeds threshold*next best
    for cat in probs:
      if cat==best: continue
      if probs[cat]*self.getthreshold(best)>probs[best]: return default
    return best

class fisherclassifier(classifier):
  
  def cprob(self,f,cat):
    # The frequency of this feature in this category    
    clf=self.fprob(f,cat)
    if clf==0: return 0

    # The frequency of this feature in all the categories
    freqsum=sum([self.fprob(f,c) for c in self.categories()])

    # The probability is the frequency in this category divided by
    # the overall frequency
    p=clf/(freqsum)
    
    # odds its in this category / sum of odds its in each category
    return p
  
  # TODO: Returns the probability of item in cat. No idea how the natural log or chi squared part works
  def fisherprob(self,item,cat):
    # Multiply all the probabilities together
    p=1
    features=self.getfeatures(item)
    for f in features:
      p*=(self.weightedprob(f,cat,self.cprob))

    # Take the natural log and multiply by -2
    fscore=-2*math.log(p)

    # Use the inverse chi2 function to get a probability
    return self.invchi2(fscore,len(features)*2)
  
  def invchi2(self,chi, df):
    m = chi / 2.0
    sum = term = math.exp(-m)
    for i in range(1, df//2):
        term *= m / i
        sum += term
    return min(sum, 1.0)
    
  def __init__(self,getfeatures):
    classifier.__init__(self,getfeatures)
    self.minimums={}

  def setminimum(self,cat,min):
    self.minimums[cat]=min
  
  def getminimum(self,cat):
    if cat not in self.minimums: return 0
    return self.minimums[cat]
    
  def classify(self,item,default=None):
    # Loop through looking for the best result
    best=default
    max=0.0
    for c in self.categories():
      p=self.fisherprob(item,c)
      # Make sure it exceeds its minimum
      if p>self.getminimum(c) and p>max:
        best=c
        max=p
    return best


def sampletrain(cl):
  cl.train('Nobody owns the water.','good')
  cl.train('the quick rabbit jumps fences','good')
  cl.train('buy pharmaceuticals now','bad')
  cl.train('make quick money at the online casino','bad')
  cl.train('the quick brown fox jumps','good')
  

if __name__ == '__main__':
    # cl = classifier(getwords)
    # cl = naivebayes(getwords)
    # cl = fisherclassifier(getwords)
    cl = fisherclassifier(feedfilter.entryfeatures)
    # cl.setdb('test1.db')
    cl.setdb('python_feed.db')
    # sampletrain(cl)
    
    # First demo
    # cl.train('the quick brown fox jumps over the lazy dog', 'good')
    # cl.train('make quick money in the online casino', 'bad')
    # print(cl.fcount('quick', 'good'))
    # print(cl.fcount('quick', 'bad'))
    
    # Probability demo
    # cl.fprob('quick', 'good')
    
    # Weighted Prob Demo
    # print(cl.weightedprob('money', 'good', cl.fprob))
    # sampletrain(cl)
    # print(cl.weightedprob('money', 'good', cl.fprob))
    
    # Bayes Demo
    # print(cl.prob('quick rabbit', 'good'))
    # print(cl.prob('quick rabbit', 'bad'))
    
    # Threshold Demo
    # print(cl.classify('quick rabbit', default='unknown'))
    # print(cl.classify('quick money', default='unknown'))
    # cl.setthreshold('bad', 3.0)
    # print(cl.classify('quick money', default='unknown'))
    # for i in range(10): 
    #   sampletrain(cl)
    # print(cl.classify('quick money', default='unknown'))
    
    # Fisher Demo
    # print(cl.cprob('quick', 'good'))
    # print(cl.cprob('quick', 'bad'))
    # print(cl.weightedprob('money', 'bad', cl.cprob))
    
    # Combining Probabilities
    # print(cl.cprob('quick', 'good'))
    # print(cl.fisherprob('quick rabbit', 'good'))
    # print(cl.fisherprob('quick rabbit', 'bad'))
    
    # Classifiers
    # print(cl.classify('quick rabbit'))
    # print(cl.classify('quick money'))
    # cl.setminimum('bad', 0.8)
    # print(cl.classify('quick money'))
    # cl.setminimum('good', 0.5)
    # print(cl.classify('quick money'))
    
    # Feed Filter
    # feedfilter.read('python_search.xml', cl)
    # print(cl.cprob('python', 'prog'))
    # print(cl.cprob('python', 'snake'))
    # print(cl.cprob('python', 'monty'))
    # print(cl.cprob('eric', 'monty'))
    # print(cl.fprob('eric', 'monty'))
    
    # Feature Detection
    feedfilter.read('python_search.xml', cl)
    