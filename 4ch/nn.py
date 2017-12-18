import pdb
from math import tanh
from pysqlite2 import dbapi2 as sqlite

def dtanh(y):
    return 1.0-y*y

class searchnet:
    def __init__(self,dbname):
        self.con=sqlite.connect(dbname)
  
    def __del__(self):
        self.con.close()

    def maketables(self):
        self.con.execute('drop table if exists hiddennode')
        self.con.execute('drop table if exists wordhidden')
        self.con.execute('drop table if exists hiddenurl')
        self.con.execute('create table hiddennode(create_key)')
        self.con.execute('create table wordhidden(fromid,toid,strength)')
        self.con.execute('create table hiddenurl(fromid,toid,strength)')
        self.con.commit()

    def getstrength(self,fromid,toid,layer):
        if layer==0: 
            table='wordhidden'
        else: 
            table='hiddenurl'
        
        res=self.con.execute('select strength from %s where fromid=%d and toid=%d' % (table,fromid,toid)).fetchone()
        if res==None: 
            # default values
            if layer==0: return -0.2
            if layer==1: return 0
        return res[0]

    def setstrength(self,fromid,toid,layer,strength):
        if layer==0: table='wordhidden'
        else: table='hiddenurl'
        res=self.con.execute('select rowid from %s where fromid=%d and toid=%d' % (table,fromid,toid)).fetchone()
        if res==None: 
            self.con.execute('insert into %s (fromid,toid,strength) values (%d,%d,%f)' % (table,fromid,toid,strength))
        else:
            rowid=res[0]
            self.con.execute('update %s set strength=%f where rowid=%d' % (table,strength,rowid))

    def generatehiddennode(self,wordids,urls):
      # Will generate a hidden node for every combination of inputs and possible outputs
        
      if len(wordids)>3: return None
      # Check if we already created a node for this set of words
      sorted_words=[str(id) for id in wordids]
      sorted_words.sort()
      createkey='_'.join(sorted_words)
      res=self.con.execute("select rowid from hiddennode where create_key='%s'" % createkey).fetchone()

      # If not, create it
      if res==None:
        cur=self.con.execute("insert into hiddennode (create_key) values ('%s')" % createkey)
        hiddenid=cur.lastrowid
        # Put in some default weights
        for wordid in wordids:
          self.setstrength(wordid,hiddenid,0,1.0/len(wordids))
        for urlid in urls:
          self.setstrength(hiddenid,urlid,1,0.1)
        self.con.commit()

    def getallhiddenids(self,wordids,urlids):
        l1={}
        for wordid in wordids:
            cur=self.con.execute('select toid from wordhidden where fromid=%d' % wordid)
            for row in cur:
                l1[row[0]]=1
        for urlid in urlids:
            cur=self.con.execute('select fromid from hiddenurl where toid=%d' % urlid)
            for row in cur:
                l1[row[0]]=1
        return l1.keys()

    def setupnetwork(self,wordids,urlids):
        # value lists
        self.wordids=wordids
        self.hiddenids=self.getallhiddenids(wordids,urlids)
        self.urlids=urlids
 
        # outputs of actual nodes
        self.ai = [1.0]*len(self.wordids)
        self.ah = [1.0]*len(self.hiddenids)
        self.ao = [1.0]*len(self.urlids)
        
        # create weights matrix
        # weights from inputs to hidden layer
        self.wi = [[self.getstrength(wordid,hiddenid,0) for hiddenid in self.hiddenids] for wordid in self.wordids]
        # weights from hidden layer to outputs
        self.wo = [[self.getstrength(hiddenid,urlid,1) for urlid in self.urlids] for hiddenid in self.hiddenids]

    def feedforward(self):
        # the only inputs are the query words
        for i in range(len(self.wordids)):
            self.ai[i] = 1.0

        # pdb.set_trace()
        # hidden activations
        # equal to a sum of all node values coming to them * input weights
        # and that sum placed in the activation function (in this case tanh)
        for j in range(len(self.hiddenids)):
            sum = 0.0
            for i in range(len(self.wordids)):
                sum = sum + self.ai[i] * self.wi[i][j]
            self.ah[j] = tanh(sum)

        # output activations
        # equal to a sum of all node vales coming to them * output weights
        # and that sum placed in the activation (in this case tanh)
        for k in range(len(self.urlids)):
            sum = 0.0
            for j in range(len(self.hiddenids)):
                sum = sum + self.ah[j] * self.wo[j][k]
            self.ao[k] = tanh(sum)

        return self.ao

    def getresult(self,wordids,urlids):
      self.setupnetwork(wordids,urlids)
      return self.feedforward()

    def backPropagate(self, targets, N=0.5):
        output_deltas = [0.0] * len(self.urlids)
        
        # pdb.set_trace()
        # calculate errors for output
        # output deltas --> dtanh(node value) * (target input - node value)
        # output deltas --> basically how much our guesses were off by
        for k in range(len(self.urlids)):
            error = targets[k]-self.ao[k]
            output_deltas[k] = dtanh(self.ao[k]) * error

        # calculate errors for hidden layer
        # hidden_deltas --> dtanh(node value) * (sum)
        # sum = sum of all output_deltas * weights
        hidden_deltas = [0.0] * len(self.hiddenids)
        for j in range(len(self.hiddenids)):
            error = 0.0
            for k in range(len(self.urlids)):
                error = error + output_deltas[k]*self.wo[j][k]
            hidden_deltas[j] = dtanh(self.ah[j]) * error

        # update output weights
        # weight update for each output--> output_delta * hidden node value * N
        # N is an input variable to decide how quickly the updates get factored in
        for j in range(len(self.hiddenids)):
            for k in range(len(self.urlids)):
                change = output_deltas[k]*self.ah[j]
                self.wo[j][k] = self.wo[j][k] + N*change

        # update input weights
        # same calc for updating input weights as for output
        for i in range(len(self.wordids)):
            for j in range(len(self.hiddenids)):
                change = hidden_deltas[j]*self.ai[i]
                self.wi[i][j] = self.wi[i][j] + N*change

    def trainquery(self,wordids,urlids,selectedurl, p=True):
        # generate a hidden node if necessary
        self.generatehiddennode(wordids,urlids)
        
        # load network from DB and feed forward to setup up node values based on DB
        self.setupnetwork(wordids,urlids)      
        self.feedforward()
        targets=[0.0]*len(urlids)
        
        if p:
            print("training input: " + str(wordids) + "    training outputs: " + str(urlids) + "    selected output: " + str(selectedurl))
            print("Before:")
            self.print_weights()
        
        # Set the chosen url to 1 and the rest to 0 and pass that to backpropigation
        targets[urlids.index(selectedurl)]=1.0
        error = self.backPropagate(targets)
        self.updatedatabase()
        # self.net_update(wordids, urlids, selectedurl)
        
        if p:
            print("After:")
            self.print_weights()
    
    def get_hidden_key(self, hidden_id):
        return self.con.execute("select create_key from hiddennode where rowid='%s'" % hidden_id).fetchone()
    
    def print_weights(self):
        print("input weights (row 1 => all weights from input node 1, etc):")
        
        k = 0
        for i in self.wi:
            inp_str = str(self.wordids[k]) + ": "
            for inp in i:
                inp_str += str(round(inp, 4)) + ", "
            inp_str = inp_str[:-2]
            print(inp_str)
            k += 1
        
        k = 0
        print("output weights (row 1 => all weights from hidden node 1, etc)::")
        for o in self.wo:
            out_str = str(self.get_hidden_key(self.hiddenids[k])[0]) + ": "
            # out_str = str(self.hiddenids[k]) + ": "
            for out in o:
                out_str += str(round(out, 4)) + ", "
            out_str = out_str[:-2]
            print(out_str)
            k += 1
    
    def net_update(self, inputs, outputs, selected_output):
        print("training input: " + str(inputs) + "    training outputs: " + str(outputs) + "    selected output: " + str(selected_output))
        print("input nodes \t hidden nodes \t output nodes")
        mx = max([len(self.ai), len(self.ah), len(self.ao)])
        for i in range(mx):
            try:
                ai = round(self.ai[i], 4)
            except:
                ai = "[null]"
            
            try:
                ah = round(self.ah[i], 4)
            except:
                ah = "[null]"
                
            try:
                ao = round(self.ao[i], 4)
            except:
                ao = "[null]"
                
            print(str(ai) + "\t\t" + str(ah) + "\t\t" + str(ao))

        self.print_weights()
    
    def updatedatabase(self):
      # set them to database values
      for i in range(len(self.wordids)):
          for j in range(len(self.hiddenids)):
              self.setstrength(self.wordids[i],self.hiddenids[j],0,self.wi[i][j])
      for j in range(len(self.hiddenids)):
          for k in range(len(self.urlids)):
              self.setstrength(self.hiddenids[j],self.urlids[k],1,self.wo[j][k])
      self.con.commit()
      

if __name__ == '__main__':
    mynet = searchnet('nn.db')
    mynet.maketables()
    wWorld, wRiver, wBank = 101, 102, 103
    uWorldBank, uRiver, uEarth = 201, 202, 203
    # mynet.generatehiddennode([wWorld, wBank], [uWorldBank, uRiver, uEarth])
      
    # demo the getresult function  
    # print(mynet.getresult([wWorld, wBank], [uWorldBank, uRiver, uEarth]))
    
    # Train query exercise
    # mynet.trainquery([wWorld, wBank], [uWorldBank, uRiver, uEarth], uWorldBank)
    # print(mynet.getresult([wWorld, wBank], [uWorldBank, uRiver, uEarth]))
    
    # Neural Network Example
    allurls = [uWorldBank, uRiver, uEarth]
    for i in range(30):
        pdb.set_trace()
        mynet.trainquery([wWorld, wBank], allurls, uWorldBank)
        pdb.set_trace()
        mynet.trainquery([wRiver, wBank], allurls, uRiver)
        pdb.set_trace()
        mynet.trainquery([wWorld], allurls, uEarth)
    # print(mynet.getresult([wWorld, wBank], allurls))
    # print(mynet.getresult([wRiver, wBank], allurls))
    # print(mynet.getresult([wBank], allurls))
    
    
    for c in mynet.con.execute('select * from wordhidden'):
        print(c)
    
    for c in mynet.con.execute('select * from hiddenurl'):
        print(c)