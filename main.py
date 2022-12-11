#!/usr/bin/python3

# uses TextBlob, feedparser, bs4, unidecode
# TB: https://textblob.readthedocs.io/en/dev/
# FP: https://pythonhosted.org/feedparser/ https://wiki.python.org/moin/RssLibraries
# BS: https://towardsdatascience.com/how-to-web-scrape-with-python-in-4-minutes-bc49186a8460
# Use: https://finnhub.io/ to simulate the market / retrieve data (60 reqs a minute are free!)

import requests
import urllib.request
import time
import feedparser
from   textblob    import TextBlob
from   bs4         import BeautifulSoup
from   statistics  import stdev, mean
from   collections import namedtuple
from   unidecode   import unidecode


sfil = lambda fun, lst : list(filter(fun, lst))
smap = lambda fun, lst : list(map   (fun, lst))
szip = lambda l_1, l_2 : list(zip   (l_1, l_2))
Summary = namedtuple('Summary', 'mean sdev N')
Feeling = namedtuple('Feeling', 'polarity subjectivity')

marketwatch_top_url = "http://feeds.marketwatch.com/marketwatch/topstories/"
marketwatch_feedurl = marketwatch_top_url

def flatten(lst):
    acc = []
    for e in lst:
        if type(e) is list: acc = acc +  e
        else              : acc = acc + [e]
    return acc

# Determine the stocks mentioned within an article's body.
def mention_list(html):
    if html == None:
        return None

    mention_section = html.find(attrs={'class':'list list--tickers'})
    if mention_section == None:
        return None

    mention_symbols = mention_section.findAll(attrs={'class':'symbol'})
    return smap(lambda x : x.get_text() if x != None else None, mention_symbols)

# Retrieve the body of an article.
def get_contents(link):
    return BeautifulSoup(requests.get(link).text, 'html.parser')

# Extract the body of the article.
def article_body(html):
    found = html.find(id='js-article__body')
    if found is None: return None
    return unidecode(found.get_text(strip=True, separator=' '))

def combine_info(alst):
    ret = {}
    for tup in alst:
        if tup is None  : continue
        if tup[0] in ret: ret[tup[0]].extend(tup[1])
        else            : ret[tup[0]] =      tup[1]
    return ret


# A heuristic to order the elements by.
def provide_rank(feel):
    r_summ = lambda x : 0.6*x.mean + 0.2*(1-x.sdev) + 0.2*(x.N/4.0)
    r_feel = lambda x : 0.5*r_summ(x.polarity) + 0.5*r_summ(x.subjectivity)

    elems = list(feel.items())
    elems.sort(key=lambda x : r_feel(x[1]), reverse=True)
    return elems

# Get an overall feeling for each stock.
def overall_feel(alst):
    sdv = lambda lst : 0 if len(lst) <= 2 else stdev(lst)
    avg = lambda lst : 0 if len(lst) == 0 else  mean(lst)
    ret = {}
    for k, v in alst.items():
        polarity = smap(lambda x : x.polarity    , v)
        subtivty = smap(lambda x : x.subjectivity, v)
        ret[k] = Feeling(Summary(avg(polarity), sdv(polarity), len(polarity)),
                         Summary(avg(subtivty), sdv(subtivty), len(subtivty)))
    return ret

# Remove elements which are not certain enough.
def keepgoodinfo(alst):
    keep_pol = lambda x : abs(x.mean) >= 0.05 # keep those polarities large enough
    keep_sub = lambda x :     x.mean  <= 0.95 # keep those not so subjective as this
    keep_bad = lambda x : keep_pol(x.polarity) and keep_sub(x.subjectivity)

    return dict(sfil(lambda x : keep_bad(x[1]), alst.items()))

# Make the returned associations nice and pretty
def pretty_print(assc):
    summary_str = lambda x : 'mean({:+5.3f}), stdev({:5.3f}), N({:5.3f})'.format(x.mean, x.sdev, x.N)
    for name, feel in assc:
        print('STOCK SYMBOL: {}\n\tSENTIMENT: {}\n\tCERTAINTY: {}'.format(
            name, summary_str(feel.polarity), summary_str(feel.subjectivity)))

# Determine the associations (+/-) within an article's body.
# Uses mention_list to determine what stock symbols to analyze.
def associations(tupl):
    if None in tupl:
        return None

    symbols = set(tupl[0])
    article = str(tupl[1]).split('.')
    ret_lst = []
    for s in symbols:
        ret_lst.append((s, smap(lambda l : TextBlob(l).sentiment,
                            filter(lambda sentence : s in sentence, article))))
    return ret_lst



#if __name__ == "__main__":
feed = feedparser.parse(marketwatch_feedurl)
if feed["bozo"] == 1:
    print("ALERT: RSS FEED WAS MALFORMED")

tops = smap(lambda x : x["link"], feed["items"])
html = smap(get_contents        ,          tops)
text = smap(article_body        ,          html)
syms = smap(mention_list        ,          html)
info = smap(associations        ,szip(syms,text))
comb = combine_info(flatten(info))
feel = overall_feel(        comb)
good = keepgoodinfo(        feel)
rank = provide_rank(        good)
pretty_print(rank)
print("DONE")

# TODO: Make a streaming thing
# TODO: Simulate stock market changes with https://finnhub.io/
