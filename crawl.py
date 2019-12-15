##### How to use the Script #######
#
#
# nohup python crawl.py {keyword} {days} &
#
# ### OUTDATED
# Bug :   On headless browser, namely PhantomJS (which has no GUI, runs in the background),
#         is not able to go back beyond 10 days or so, whereas with firefox webdriver
#         (which opens up a firefox gui) we can go beyond as much as we like, currently it is tested for 25 days.
#
# ### UPDATE : 15-12-2019
# Due to Twitter's limit, only 10 days worth of scrolling can be done.
# Check with reading the data back form the saved file, there might be errors due to encodings
#####################################


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoAlertPresentException
import sys
import time
import dateparser
from datetime import datetime
import time, re
from bs4 import BeautifulSoup as BS
import json
import logging


class Sel():
    def __init__(self):
        self.driver = webdriver.Firefox()
        # self.driver = webdriver.PhantomJS()
        # self.driver.set_window_size(1120, 550)
        # self.driver.implicitly_wait(30) #### commention as we are using
        self.base_url = "https://twitter.com"
        self.verificationErrors = []
        self.accept_next_alert = True
        logging.info("Initialization Completed")

    def __del__(self):
        self.driver.close()
        self.driver.quit()
        logging.info("Cleaned and Deleted the Webdriver Instance")

    def crawlScroll(self, keyword, days, outputFileName):
        retrievalDays = int(days)
        url = "/search?q=" + keyword + "&src=typd"
        self.driver.get(self.base_url + url)
        wait = WebDriverWait(self.driver, 30)            ### 30 sec timeout for Ajax to load

        currentTime = datetime.now()
        loopingContinue = True
        tweetMap = {}                           #### container for the tweet ids, checking for unique ids each time we scroll.
        logging.info("Starting to Scroll ... ")
        pageEndCheck = 0

        while(loopingContinue):
            html = self.driver.page_source
            soup = BS(html, "lxml")
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            orderedList = soup.find_all("ol", {"class": "stream-items js-navigable-stream"})
            for tweetOL in orderedList:
                # tweetList = tweetOL.find_all('li', {"class": "js-stream-item stream-item stream-item expanding-stream-item\n"})
                tweetList = tweetOL.find_all('li', {"class": "js-stream-item stream-item stream-item"})
                if len(tweetList) == 0:
                    print("No Data for this keyword !!!")
                    return
                for tweetElement in tweetList:
                    tweetData = {}                                      #### container for the tweet data, renewed for every tweet
                    innerDivElementList = tweetElement.find_all('div')
                    for innerDiv in innerDivElementList:
                        if innerDiv.has_attr('data-name'):
                            tweetData['Tweet Id'] = innerDiv.get('data-tweet-id').encode('utf-8')
                            if innerDiv.get('data-tweet-id').encode('utf-8') in tweetMap:
                                tweetMap[innerDiv.get('data-tweet-id').encode('utf-8')] += 1
                            else:
                                tweetMap[innerDiv.get('data-tweet-id').encode('utf-8')] = 1
                            tweetData['User Screen Name'] = innerDiv.get('data-name').encode('utf-8')
                            tweetData['User Login Name'] = innerDiv.get('data-screen-name').encode('utf-8')
                            tweetData['User Id'] = innerDiv.get('data-user-id').encode('utf-8')
                            if innerDiv.has_attr('data-mentions'):
                                tweetData['Users Referenced'] = innerDiv.get('data-mentions').encode('utf-8')
                            else:
                                tweetData['Users Referenced'] = ' '
                        if innerDiv.has_attr('class') and ' '.join(i for i in innerDiv['class'] if i.strip() != '') == 'js-tweet-text-container':
                            tweetData['Tweet'] = innerDiv.get_text().strip().encode('utf-8')
                        if innerDiv.has_attr('class') and ' '.join(i for i in innerDiv['class'] if i.strip() != '') == 'ProfileTweet-action ProfileTweet-action--retweet js-toggleState js-toggleRt':
                            if len((innerDiv.get_text().strip()).split()) > 2:
                                tweetData['Retweets'] = (innerDiv.get_text().strip().encode('utf-8')).split()[1]
                            else :
                                tweetData['Retweets'] = '0'
                        if innerDiv.has_attr('class') and ' '.join(i for i in innerDiv['class'] if i.strip() != '') == 'ProfileTweet-action ProfileTweet-action--favorite js-toggleState':
                            if len((innerDiv.get_text().strip()).split()) > 2:
                                tweetData['Likes'] = (innerDiv.get_text().strip().encode('utf-8')).split()[1]
                            else :
                                tweetData['Retweets'] = '0'
                    innerAElementList = tweetElement.find_all('a')
                    for innerA in innerAElementList:
                        if innerA.has_attr('title') and innerA.has_attr('class'):
                            if ' '.join(i for i in innerA['class'] if i.strip() != '') == 'tweet-timestamp js-permalink js-nav js-tooltip':
                                timeStamp = ','.join([innerA.get('title').split('-')[1].strip(),innerA.get('title').split('-')[0].strip()])
                                tweetData['Time Stamp'] = dateparser.parse(timeStamp).strftime("%Y-%m-%d %H:%M:%S")
                                if (currentTime - dateparser.parse(timeStamp)).days > retrievalDays:
                                    loopingContinue = False
                    if tweetData:
                        if tweetData['Tweet Id'] in tweetMap:
                            if tweetMap[tweetData['Tweet Id']] == 1:
                                data = {str(k): str(v) for k, v in tweetData.items()}
                                with open(outputFileName, 'a') as f:
                                    # json.dump(tweetData, f, ensure_ascii=False)
                                    # logging.info("Data : %s", json.dumps(tweetData, ensure_ascii=False, encoding='utf8'))
                                    json.dump(data, f)
                                    logging.info("Data : %s", json.dumps(data))
                                    f.write('\n')
            if any(v == 1 for v in tweetMap.values()):
                pageEndCheck = 0
            elif pageEndCheck == 20:
                loopingContinue = False
                logging.info("No more results on the Search Page....")
                logging.info("Terminating the Scrolling.")
                return
            else:
                logging.info("The scroll returned the same page")
                pageEndCheck += 1

            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            # time.sleep(10)
            try:
                wait.until(lambda driver: self.driver.execute_script("return jQuery.active == 0"))
                time.sleep(5)
            except Exception as e:
                logging.exception("Error Timed-Out waiting for the AJAX response : %s",e)
                logging.info("Reloading the complete search page then restarting the Crawling")
                self.driver.get(self.base_url + url)
                logging.info("Page reloaded, Begining to scroll")
                time.sleep(10)
        return


def main(argv):
    keyword = argv[0]
    days = int(argv[1])
    outputFileName = keyword+'-Data.log'
    selenium = Sel()
    selenium.crawlScroll(keyword, days, outputFileName)


if __name__ == "__main__":
    loggingFileName = 'Runtime-TwitterCrawler-'+str(sys.argv[1])+'.log'
    logging.basicConfig(level=logging.INFO, filename=loggingFileName , format='[%(levelname)s] (%(threadName)-10s) %(asctime)s : %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    main(sys.argv[1:])
    logging.info("Exting the code")
