from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


def sentiment_scores(sentence):
    analyser = SentimentIntensityAnalyzer()
    snt = analyser.polarity_scores(sentence)
    return snt['compound']


def get_sentiment(ans_list):
    scores_list = [[], [], []]
    sentiment_list = []
    for day in range(len(ans_list)):
        if len(ans_list[day]) != 0:
            for i in range(len(ans_list[day])):
                ans = ans_list[day][i]
                scores_list[day].append(sentiment_scores(ans))

    for day in range(len(scores_list)):
        if len(scores_list[day]) == 0:
            sentiment_list.append(-2)
        else:
            counter = 0
            for i in range(len(scores_list[day])):
                counter += scores_list[day][i]
            sentiment = counter / len(scores_list[day])
            sentiment_list.append(sentiment)

    return sentiment_list


def get_sentiment_one_string_per_day(ans_list):
    scores_list = []
    ans = ""
    for day in range(len(ans_list)):
        if len(ans_list[day]) != 0:
            for i in range(len(ans_list[day])):
                answer = ans_list[day][i]
                if not answer.endswith('.'):
                    answer = answer + "."
                ans = ans + " " + answer
            scores_list.append(sentiment_scores(ans))
            ans = ""
        else:
            scores_list.append(-2)

    return scores_list

