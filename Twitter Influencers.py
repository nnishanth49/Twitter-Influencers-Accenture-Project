# -*- coding: utf-8 -*-
"""
Created on Sun Nov 20 12:31:30 2016

@author: Nishanth Narala
"""

import tweepy
import pandas as pd
import numpy as np
import datetime
import time


# Function for creating API Object.
def CreateAPIObject(ConsumerKey, ConsumerSecret, AccessToken, AccessSecret):
    auth = tweepy.OAuthHandler(ConsumerKey, ConsumerSecret)
    auth.set_access_token(AccessToken, AccessSecret)
    return tweepy.API(auth, wait_on_rate_limit_notify = True)


# Function for getting the query from the user
def GetQueries():
    queryList = list()
    print '''Enter the query you want to search on twitter (ex. "chief analytics officer", "chief data officer", "chief data scientist").\nYou can add multiple queries one by one and when you are done, enter "done".'''
    while True:
        query = raw_input('Query : ')
        if query == '':
            print "A query cannot be empty. Enter 'done' if you are finished entering the queries."
            continue
        if query == 'done':
            if len(queryList) == 0:
                print "User must enter at least 1 query to proceed."
                continue
            else: break
        else:
            queryList.append(query)
    return queryList


# Function for getting twitter handles and exporting a csv of search results.
def GetTwitterHandles(queryList, apiObject):
    count = 200
    api = apiObject    
    users = list()
    twitterHandles = list()
    for query in queryList:
        for user in tweepy.Cursor(api.search_users, query, count = 200).items(count):
            if user._json not in users and user.protected != True:
                users.append(user._json)
                twitterHandles.append(user._json['screen_name'].encode("utf-8"))
            else: continue
    print "The query returned {} twitter handles".format(len(twitterHandles))
    
    column = list()
    column = ['Target Person Name', 'Twitter Handle', 'Location', 'Joined Twitter', 'Profile Description', 'Total # Followers', 'Total # Following', 'Total # Tweets','Tweets Favourited', 'User ID']
    data = dict()
    data = {'Target Person Name' : [targetDetails['name'] for targetDetails in users],
            'Twitter Handle' : [targetDetails['screen_name'] for targetDetails in users],
            'Location' : [targetDetails['location'] for targetDetails in users],
            'Joined Twitter' : [targetDetails['created_at'] for targetDetails in users],
            'Profile Description' : [targetDetails['description'] for targetDetails in users],
            'Total # Followers' : [targetDetails['followers_count'] for targetDetails in users],
            'Total # Following' : [targetDetails['friends_count'] for targetDetails in users],
            'Total # Tweets' : [targetDetails['statuses_count'] for targetDetails in users],
            'Tweets Favourited' : [targetDetails['favourites_count'] for targetDetails in users],
            'User ID' : [targetDetails['id'] for targetDetails in users]
            }
    targetSetDF = pd.DataFrame(data, columns = column)
    targetSetDF.to_csv('Target Information.csv', sep = ',', encoding = 'utf-8')
    
    return twitterHandles


# Function for calculating score.
def CalculateScore(dictionary, maxScore, scoreIncrements):
    totalBins = maxScore / scoreIncrements
    column = ['Name', 'Count', 'Percentage']
    data = dict()
    data = {'Name' : dictionary.keys(),
            'Count' : dictionary.values()
            }    
    dataFrame = pd.DataFrame(data, columns = column)
    percentage = [value * 100.0 / sum(dataFrame['Count']) for value in dictionary.values()]
    dataFrame['Percentage'] = percentage
    scoreList = list()    
    if len(dataFrame) > 0:
        binSize = (max(dataFrame['Percentage']) - min(dataFrame['Percentage'])) / totalBins
        bins = np.arange(min(dataFrame['Percentage']) + binSize, max(dataFrame['Percentage']), binSize)
        for percent in dataFrame['Percentage']:
            score = scoreIncrements
            flag = 0
            for singleBin in bins:
                if percent <= singleBin and flag != 1:
                    scoreList.append(score)
                    flag = 1
                    break
                else:
                    score += scoreIncrements
                    continue
            if flag != 1:
                scoreList.append(maxScore)
    
    dataFrame['Score'] = scoreList
    dataFrame = dataFrame.sort_values(by = 'Score', axis = 0, ascending = False)
    return dataFrame
        

# Function for combining the results for an influencer
def UserAnalysis(userTwitterHandle, apiObject, accessTokenList, accessSecretList, consumerKeyList, consumerSecretList):
    global i
    # Tweepy Rate Limit Exception Handlers.
    def CursorLimitHandlerFavorite(cursor, favoriteCount, accessTokenList, accessSecretList, consumerKeyList, consumerSecretList):
        global i        
        x = 0
        index = 0
        while True:
            try:
                index = cursor.page_iterator.index
                yield cursor.next()
                x += 1
                if favoriteCount <= x: break
            
            except tweepy.RateLimitError:
                print "Exception Code Started for Favorites"
                print "i = ", i
                print 'index = ', index
                if i < (len(accessTokenList) - 1):                
                    i += 1                    
                    api = CreateAPIObject(consumerKeyList[i], consumerSecretList[i],accessTokenList[i], accessSecretList[i])
                    cursor = tweepy.Cursor(api.favorites, screen_name = user, count = 200).items(favoriteCount - x)
                    cursor.page_iterator.index = index
                else:
                    print "Rate Limit Reached for all tokens. Sleeping for 15 minutes."               
                    time.sleep(15 * 60)
                    i = 0
                    api = CreateAPIObject(consumerKeyList[i], consumerSecretList[i],accessTokenList[i], accessSecretList[i])
                    cursor = tweepy.Cursor(api.favorites, screen_name = user, count = 200).items(favoriteCount - x)
                    cursor.page_iterator.index = index
            
            except tweepy.TweepError as te:
#                if int(te.message[0]['code']) in [502, 503, 504]:
#                    print "Problem with Twitter Servers./nThe process will resume in 2 minutes"
#                    time.sleep(2 * 60)
                print "Problem with Twitter Servers.\nThe process will resume in 2 minutes"
                time.sleep(2 * 60)
    # Tweepy Rate Limit Exception Handlers.
    def CursorLimitHandlerFriend(cursor, friendCount, accessTokenList, accessSecretList, consumerKeyList, consumerSecretList):
        global i        
        x = 0
        nxtCursor = 0
        while True:
            try:
                nxtCursor = cursor.page_iterator.next_cursor            
                yield cursor.next()
                x += 1
                if friendCount <= x: break
            except tweepy.RateLimitError:
                print "Exception Code Started for Friends"
                print "i = ", i
                print "next cursor = ", nxtCursor               
                if i < (len(accessTokenList) - 1):
                    i += 1
                    api = CreateAPIObject(consumerKeyList[i], consumerSecretList[i],accessTokenList[i], accessSecretList[i])
                    cursor = tweepy.Cursor(api.friends, screen_name = user, count = 200).items(friendCount - x)
                    cursor.page_iterator.next_cursor = nxtCursor
                else:
                    print "Rate Limit Reached for all tokens. Sleeping for 15 minutes."
                    time.sleep(15 * 60)
                    i = 0
                    api = CreateAPIObject(consumerKeyList[i], consumerSecretList[i],accessTokenList[i], accessSecretList[i])
                    cursor = tweepy.Cursor(api.friends, screen_name = user, count = 200).items(friendCount - x)
                    cursor.page_iterator.next_cursor = nxtCursor
                    
            except tweepy.TweepError as te:
#                if int(te.message[0]['code']) in [502, 503, 504]:
#                    print "Problem with Twitter Servers./nThe process will resume in 2 minutes"
#                    time.sleep(2 * 60)
                print "Problem with Twitter Servers.\nThe process will resume in 2 minutes"
                time.sleep(2 * 60)
                    
    # Tweepy Rate Limit Exception Handlers.
    def CursorLimitHandlerTimeline(cursor, statusCount, accessTokenList, accessSecretList, consumerKeyList, consumerSecretList):
        global i
        x = 0
        index = 0
        while True:
            try:
                index = cursor.page_iterator.index          
                yield cursor.next()
                x += 1
                if statusCount <= x: break
            except tweepy.RateLimitError:
                print "Exception Code Started for Timeline"
                print "i = ", i
                print 'index = ', index
                if i < (len(accessTokenList) - 1):
                    i += 1
                    api = CreateAPIObject(consumerKeyList[i], consumerSecretList[i],accessTokenList[i], accessSecretList[i])
                    cursor = tweepy.Cursor(api.user_timeline, screen_name = user, count = 200).items(statusCount - x)
                    cursor.page_iterator.index = index
                else:
                    print "Rate Limit Reached for all tokens. Sleeping for 15 minutes."
                    time.sleep(15 * 60)
                    i = 0
                    api = CreateAPIObject(consumerKeyList[i], consumerSecretList[i],accessTokenList[i], accessSecretList[i])
                    cursor = tweepy.Cursor(api.user_timeline, screen_name = user, count = 200).items(statusCount - x)
                    cursor.page_iterator.index = index
                    
            except tweepy.TweepError as te:
#                if int(te.message[0]['code']) in [502, 503, 504]:
#                    print "Problem with Twitter Servers./nThe process will resume in 2 minutes"
#                    time.sleep(2 * 60)
                print "Problem with Twitter Servers.\nThe process will resume in 2 minutes"
                time.sleep(2 * 60)
    
    
    # maximum score and increments. Used when CalculateScore Method is called.    
    maxScore = 100.0
    scoreIncrements = 0.1
    
    # User
    user = userTwitterHandle
    api = apiObject
   
   # Getting the details of a person.
    flag = 0
    while(flag == 0):
        try:
            details = api.get_user(screen_name = user)
            flag = 1
        except tweepy.TweepError as te:
            print te.reason
            print "Problem with the Internet Connection or Twitter Servers.\nThe process will resume in 2 minutes"
            time.sleep(2 * 60)
        except tweepy.RateLimitError:
            print "A Rate Limit Exception was raised while getting the details of {}".format(user)
            print "Retrying!"
            if i < (len(accessTokenList) - 1):
                i += 1
                api = CreateAPIObject(consumerKeyList[i], consumerSecretList[i], accessTokenList[i], accessSecretList[i])
            else:
                i = 0
                api = CreateAPIObject(consumerKeyList[i], consumerSecretList[i], accessTokenList[i], accessSecretList[i])

    
#    print "Twitter Handle : ", details.screen_name
#    print "Favorites count : ", details.favourites_count
#    print "Followers count : ", details.followers_count
#    print "Following count : ", details.friends_count
#    print "Joined Twitter : ", details.created_at
#    print "Total No. of Tweets : ", details.statuses_count
    
    # Fetching the date 
    if (datetime.datetime.now() - datetime.timedelta(days = 2 * 365)) > details.created_at:
        tweetsAfterDate = (datetime.datetime.now() - datetime.timedelta(days = 2 * 365))
    else:
        tweetsAfterDate = details.created_at    
    
    # Getting user timeline.
    timeline = list()
    for tweets in CursorLimitHandlerTimeline(tweepy.Cursor(api.user_timeline, screen_name = user, count = 200).items(details.statuses_count), details.statuses_count, accessTokenList, accessSecretList, consumerKeyList, consumerSecretList):
        if tweets.created_at > tweetsAfterDate:
            if tweets._json not in timeline:
                timeline.append(tweets._json)
        else: break
        
    # Extracting Mentions
    mentions = list()
    for tweet in timeline:
        if (len(tweet['entities']['user_mentions']) > 0) and ('retweeted_status' not in tweet.keys()):
            for mention in tweet['entities']['user_mentions']:
                if mention['screen_name'].encode("utf-8") != user:
                    mentions.append(mention['screen_name'].encode("utf-8"))
                else:
                    continue
    
    # Mention dictionary
    mentionDict = dict()
    for mention in mentions:
        if mention in mentionDict:
            mentionDict[mention] += 1
        else:
            mentionDict[mention] = 1
    
    # Extracting Retweets
    retweets = list()
    for tweets in timeline:
        if 'retweeted_status' in tweets.keys():
            retweets.append(tweets)
        
    # Making a dictionary of retweet and extracting the followers of the retweeted persons
    retweetDictionary = dict()
    retweetedPersonDict = dict()
    for retweet in retweets:
        if retweet['retweeted_status']['user']['screen_name'].encode("utf-8") != retweet['user']['screen_name'].encode("utf-8"):
            if retweet['retweeted_status']['user']['screen_name'].encode("utf-8") not in retweetDictionary:
                retweetDictionary[retweet['retweeted_status']['user']['screen_name'].encode("utf-8")] = 1
                retweetedPersonDict[retweet['retweeted_status']['user']['screen_name'].encode("utf-8")] = retweet['retweeted_status']['user']['followers_count']
            else:
                retweetDictionary[retweet['retweeted_status']['user']['screen_name'].encode("utf-8")] += 1
    
        
    ############################### Favorites ##############################################
    
    # Extract Favorites and the Followers of the Person favorited.
    favorites = list()
    for favorite in CursorLimitHandlerFavorite(tweepy.Cursor(api.favorites, screen_name = user, count = 200).items(details.favourites_count), details.favourites_count, accessTokenList, accessSecretList, consumerKeyList, consumerSecretList):
        if favorite.created_at > tweetsAfterDate:
            if favorite._json not in favorites:
                favorites.append(favorite._json)
        else: 
            break    
        
    favoritedHandles = dict()
    favoritedPersonFollowers = dict()
    for favoriteTweet in favorites:
        if favoriteTweet['user']['screen_name'].encode("utf-8") != user:
            if favoriteTweet['user']['screen_name'].encode("utf-8") in favoritedHandles:
                favoritedHandles[favoriteTweet['user']['screen_name'].encode("utf-8")] += 1
            else:
                favoritedHandles[favoriteTweet['user']['screen_name'].encode("utf-8")] = 1
                favoritedPersonFollowers[favoriteTweet['user']['screen_name'].encode("utf-8")] = favoriteTweet['user']['followers_count']
    
    ###################### Getting the Friends of the User ################################
    friends = list()
    for friend in CursorLimitHandlerFriend(tweepy.Cursor(api.friends, screen_name = user, count = 200).items(details.friends_count), details.friends_count, accessTokenList, accessSecretList, consumerKeyList, consumerSecretList):
        if friend._json not in friends:
            friends.append(friend._json)
        else: continue
    
    friendNames = [friend['screen_name'].encode("utf-8") for friend in friends]
    
    ################################ Analysis on Retweets, Mentions and Favorites ################################
    
    retweetDataFrame = CalculateScore(retweetDictionary, maxScore, scoreIncrements)
    favoritedHandlesDataFrame = CalculateScore(favoritedHandles, maxScore, scoreIncrements)
    mentionsDataFrame = CalculateScore(mentionDict, maxScore, scoreIncrements)
    
    ######################## Combining the Results ########################################
    #CombineCounts(retweetDictionary,favoritedHandles,mentionDict,friendNames)
    column = list(['Name', 'Favorite Score', 'Mention Score', 'Retweet Score', 'Follow/NoFollow Score'])
    data = dict()
        
    # Adding all the names in Mention Dictionary to a List.
    names = list(set(mentionDict.keys() + favoritedHandles.keys() + retweetDictionary.keys()))
   
   # Fetching the entries from the Data Frames
    favoriteScore = list()
    mentionScore = list()
    retweetScore = list()
    followScore = list()
    maxFollowScore = 100.0
    minFollowScore = 0.0

    for name in names:
        if name in list(favoritedHandlesDataFrame['Name']):
            favoriteScore.append(float(favoritedHandlesDataFrame[favoritedHandlesDataFrame['Name'] == name]['Score']))
        else:
            favoriteScore.append(0.0)
    
        if name in list(mentionsDataFrame['Name']):
            mentionScore.append(float(mentionsDataFrame[mentionsDataFrame['Name'] == name]['Score']))
        else:
            mentionScore.append(0.0)
            
        if name in list(retweetDataFrame['Name']):
            retweetScore.append(float(retweetDataFrame[retweetDataFrame['Name'] == name]['Score']))
        else:
            retweetScore.append(0.0)
            
        if name in friendNames:
            followScore.append(float(maxFollowScore))
        else:
            followScore.append(float(minFollowScore))
    
    data = {'Name' : names,
            'Favorite Score' : favoriteScore,
            'Mention Score' : mentionScore,
            'Retweet Score' : retweetScore,
            'Follow/NoFollow Score' : followScore
            }
    
    combinedResultsDataFrame = pd.DataFrame(data, columns = column)
    
    # Getting the weights
    retweetWeight, favoriteWeight, mentionWeight = GetWeights(retweets, favorites, mentions)    
    
    
    combinedResultsDataFrame['Retweet Score'] = combinedResultsDataFrame['Retweet Score'] * retweetWeight
    combinedResultsDataFrame['Favorite Score'] = combinedResultsDataFrame['Favorite Score'] * favoriteWeight
    combinedResultsDataFrame['Mention Score'] = combinedResultsDataFrame['Mention Score'] * mentionWeight
    

    # Adding all the scores
    combinedResultsDataFrame['Total Score'] = combinedResultsDataFrame['Favorite Score'] + combinedResultsDataFrame['Mention Score'] + combinedResultsDataFrame['Retweet Score'] + combinedResultsDataFrame['Follow/NoFollow Score']
    combinedResultsDataFrame = combinedResultsDataFrame.sort_values(by = 'Total Score', axis = 0, ascending = False)
#    combinedResultsDataFrame.to_csv('{} Results.csv'.format(user), sep=',', encoding='utf-8')
    return combinedResultsDataFrame
    

def OverallAnalysis(listOfDataFrames):
    allNames = list()
    for dataframe in listOfDataFrames:
        for name in list(dataframe['Name']):
            if name not in allNames:
                allNames.append(name)
            else: continue
    
    overallFollowers = list()
    overallScore = list()
    for name in allNames:
        followers = 0    
        score = 0    
        for dataframe in listOfDataFrames:
            if name in list(dataframe['Name']):
                score += float(dataframe[dataframe['Name'] == name]['Total Score'])
                if float(dataframe[dataframe['Name'] == name]['Follow/NoFollow Score']) > 0.0:
                    followers += 1
            else:
                continue
        overallFollowers.append(followers)
        overallScore.append(score)

    column = list(('Name','Overall Score'))
    data = {'Name' : allNames,
            'Overall Score' : overallScore
            }
    overallDataFrame = pd.DataFrame(data, columns = column)
    overallDataFrame['Average Score'] = overallDataFrame['Overall Score'] / len(listOfDataFrames)
    overallDataFrame['Follower (%)'] = np.array(overallFollowers) * 100.0 / len(listOfDataFrames)

    # Sorting the data frame and creating a csv.    
    overallDataFrame = overallDataFrame.sort_values(by = 'Average Score', axis = 0, ascending = False)
    overallDataFrame.to_csv('Overall Results.csv', separator = ',', encoding = 'utf-8')
 

def GetWeights(retweets, favorites, mentions):
    if len(retweets) != 0:
        weightRetweet = len(retweets) / float(len(favorites) + len(mentions) + len(retweets))
    else: weightRetweet = 0        

    if len(favorites) != 0:
        weightFavorite = len(favorites) / float(len(favorites) + len(mentions) + len(retweets))
    else: weightFavorite = 0
        
    if len(mentions) != 0:
        weightMentions = len(mentions) / float(len(favorites) + len(mentions) + len(retweets))
    else: weightMentions = 0
    
    return list([weightRetweet, weightFavorite, weightMentions])

def main():
    
    AccessToken = ""
    AccessSecret = ""
    ConsumerKey = ""
    ConsumerSecret = ""
    
    AccessTokenList = list()
    AccessSecretList = list()
    ConsumerKeyList = list()
    ConsumerSecretList = list()
    
    handle = open("AccessTokens.txt")
    for line in handle:
        if line.startswith("AccessToken"):
            AccessTokenList.append(line.split()[2])
            
        if line.startswith("AccessSecret"):
            AccessSecretList.append(line.split()[2])
            
        if line.startswith("ConsumerKey"):
            ConsumerKeyList.append(line.split()[2])
            
        if line.startswith("ConsumerSecret"):
            ConsumerSecretList.append(line.split()[2])
    handle.close()
    
    api = CreateAPIObject(ConsumerKey, ConsumerSecret, AccessToken, AccessSecret)
    
    queryList = GetQueries()
    twitterHandle = GetTwitterHandles(queryList, api)
    proceed = raw_input("Do you want to start the analysis (y/n) ? : ")
    global i
    if proceed.lower() == 'y':
        listOfDataFrames = list() 
        i = 0
        for user in twitterHandle:
            print "Value of i for {} is {}".format(user, i)
            api = CreateAPIObject(ConsumerKeyList[i], ConsumerSecretList[i], AccessTokenList[i], AccessSecretList[i])
            analysis = UserAnalysis(user, api, AccessTokenList, AccessSecretList, ConsumerKeyList, ConsumerSecretList)
            listOfDataFrames.append(analysis)
        ################## Overall Results #######################
        print "\nOverall Analysis Started."
        OverallAnalysis(listOfDataFrames)
        print "\nOverall Analysis Completed."
    
        
if __name__ == "__main__" : main()