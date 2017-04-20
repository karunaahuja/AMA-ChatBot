#!/bin/python3

import sys
import praw
#import logging
#import json

# uncomment to turn on logging and debug PRAW requests to Reddit API
# handler = logging.StreamHandler()
# handler.setLevel(logging.DEBUG)
# logger = logging.getLogger('prawcore')
# logger.setLevel(logging.DEBUG)
# logger.addHandler(handler)

questions_file = 'science-technology-questions.txt'
answers_file = 'science-technology-answers.txt'

def get_question_answer_pairs(subreddit, query_str, questions_file, answers_file):
    # get submissions in a subreddit
    submission_count = 0
    estimate_data = {} # dict: submission number-> number of question-answer pairs
    # sort by: relevance, hot, top, new, or comments
    for submission in subreddit.search(syntax='lucene', query=query_str, sort='comments', limit=1000):
        submission_count += 1
        if submission_count % 100 == 0:
            print(submission_count, submission.title, submission.url, ', author:', submission.author)

        submission_author = submission.author
        submission.comments.replace_more(limit=0)
        top_level_comments = list(submission.comments)
        question_answer_pairs_count = 0
        for tl_comment in top_level_comments:
            question_author = tl_comment.author
            question = tl_comment.body

            for reply in tl_comment.replies:
                answer_author = reply.author
                if answer_author == submission_author:
                    answer = reply.body
                    # replace all newlines with space
                    question = question.replace('\r\n', ' ')
                    answer = answer.replace('\r\n', ' ')
                    question = question.replace('\r', ' ')
                    answer = answer.replace('\r', ' ')
                    question = question.replace('\n', ' ')
                    answer = answer.replace('\n', ' ')
                    # write question and answer to separate text files, one per line
                    with open(questions_file, mode='a') as fq:
                        fq.write(question + '\n')
                    with open(answers_file, mode='a') as fa:
                        fa.write(answer + '\n')
                    question_answer_pairs_count += 1
        estimate_data[submission_count] =  question_answer_pairs_count
    return submission_count, estimate_data

def sum_estimate_data(data):
    estimate_pairs = 0
    for sub in data:
        estimate_pairs += data[sub]
    return estimate_pairs

def main(reddit_uname, reddit_cli_id, reddit_cli_secret):
    my_cli_id = reddit_cli_id
    my_cli_secret = reddit_cli_secret
    my_user_agent = ''.join(['python:AskMeAboutX:v0.1.0 (by /u/', reddit_uname, ')'])

    # get a read-only Reddit instance
    reddit = praw.Reddit(client_id=my_cli_id,
                         client_secret=my_cli_secret,
                         user_agent=my_user_agent)
    print(reddit.read_only)

    # get a subreddit
    subreddit = reddit.subreddit('IAmA')

    print(subreddit.display_name)  # Output: redditdev
    print(subreddit.title)         # Output: reddit Development
    # print(subreddit.description)   # Output: A subreddit for discussion of ...

    # TODO: check if questions_file, answers_file already exist, if so delete them

    science_submissions, science_estimate = get_question_answer_pairs(subreddit, 'flair:science', questions_file, answers_file)
    science_qa_count = sum_estimate_data(science_estimate)
    science_submissions, science_qa_count

    tech_submissions, tech_estimate = get_question_answer_pairs(subreddit, 'flair:technology', questions_file, answers_file)
    tech_qa_count = sum_estimate_data(tech_estimate)
    tech_submissions, tech_qa_count

    # music_submissions, music_estimate = get_question_answer_pairs(subreddit, 'flair:music', questions_file, answers_file)
    # music_qa_count = sum_estimate_data(music_estimate)
    # music_submissions, music_qa_count

    total_submissions = science_submissions + tech_submissions #  + music_submissions
    total_qa_pairs = science_qa_count + tech_qa_count #  + music_qa_count
    total_submissions, total_qa_pairs

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print('usage: python3 reddit.py <reddit username> <reddit OAuth client ID> <reddit OAuth secret>')
    else:
        reddit_name = sys.argv[1]
        reddit_id = sys.argv[2]
        reddit_secret = sys.argv[3]
        main(reddit_name, reddit_id, reddit_secret)
