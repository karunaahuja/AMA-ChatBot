#!/bin/python3

import sys
import praw
import string
#import logging
#import json

# uncomment to turn on logging and debug PRAW requests to Reddit API
# handler = logging.StreamHandler()
# handler.setLevel(logging.DEBUG)
# logger = logging.getLogger('prawcore')
# logger.setLevel(logging.DEBUG)
# logger.addHandler(handler)

# TODO: add exception handling for when reddit returns http status 503

TRUNC_WORDS_LIMIT = 50

questions_file = 'iama-science-technology-questions.txt'
answers_file = 'iama-science-technology-answers.txt'

def replace_newlines(content):
    return content.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ').replace('-', ' ')

def truncate(content, limit):
    words_lst = content.split(' ')
    if len(words_lst) > limit:
        return ' '.join(words_lst[0:limit])
    else:
        return content

def normalize(content):
    content = ''.join([ch for ch in content if ch not in string.punctuation])
    return content.lower()

def write_to_qa_files(question, answer, questions_file, answers_file, blacklist):
    if question not in blacklist and answer not in blacklist:
        # replace all newlines with space
        question = replace_newlines(question)
        answer = replace_newlines(answer)
        question = truncate(question, TRUNC_WORDS_LIMIT)
        answer = truncate(answer, TRUNC_WORDS_LIMIT)
        question = normalize(question)
        answer= normalize(answer)
        # write question and answer to separate text files, one per line
        with open(questions_file, mode='a') as fq:
            fq.write(question + '\n')
        with open(answers_file, mode='a') as fa:
            fa.write(answer + '\n')
        return True
    return False

def get_question_answer_pairs(subreddit, query_str, questions_file, answers_file):
    blacklist = set(['[deleted]', '[removed]'])

    # get submissions in a subreddit
    submission_count = 0
    estimate_data = {} # dict: submission number-> number of question-answer pairs
    # sort by: relevance, hot, top, new, or comments
    total_qa_count = 0
    for submission in subreddit.search(syntax='lucene', query=query_str, sort='comments', limit=1000):
        submission_count += 1
        if submission_count % 100 == 0:
#             print(submission_count, submission.title, submission.url, ', author:', submission.author)
            print(total_qa_count, submission_count, submission.title)

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
                    if write_to_qa_files(question, answer, questions_file, answers_file, blacklist):
                        question_answer_pairs_count += 1

        total_qa_count += question_answer_pairs_count
    return submission_count, total_qa_count

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

    print(subreddit.display_name)
    print(subreddit.title)

    # TODO: check if questions_file, answers_file already exist, if so delete them

    num_submissions_science, qa_count_science = get_question_answer_pairs(subreddit, 'flair:science', questions_file, answers_file)

    num_submissions_tech, qa_count_tech = get_question_answer_pairs(subreddit, 'flair:technology', questions_file, answers_file)

    total_submissions = num_submissions_science + num_submissions_tech
    total_qa_pairs = qa_count_science + qa_count_tech
    print(total_submissions, total_qa_pairs)

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print('usage: python3 reddit.py <reddit username> <reddit OAuth client ID> <reddit OAuth secret>')
    else:
        reddit_name = sys.argv[1]
        reddit_id = sys.argv[2]
        reddit_secret = sys.argv[3]
        main(reddit_name, reddit_id, reddit_secret)
