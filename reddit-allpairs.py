#!/bin/python3

import sys
import praw
import string
#import json
#import logging

# uncomment to turn on logging and debug PRAW requests to Reddit API
# handler = logging.StreamHandler()
# handler.setLevel(logging.DEBUG)
# logger = logging.getLogger('prawcore')
# logger.setLevel(logging.DEBUG)
# logger.addHandler(handler)

# TODO: add exception handling for when reddit returns http status 503

TRUNC_WORDS_LIMIT = 50

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

def get_question_answer_pairs(subreddit, questions_file, answers_file):
    blacklist = set(['[deleted]', '[removed]'])

    # get submissions in a subreddit
    submission_count = 0
    total_qa_count = 0
    for submission in subreddit.submissions(start=0):
        submission_count += 1
        if submission_count % 100 == 0:
            print(total_qa_count, submission_count, submission.title)

        submission.comments.replace_more(limit=0)
        top_level_comments = list(submission.comments)
        question_answer_pairs_count = 0
        question = submission.title
        if len(top_level_comments) > 0:
            top_comment = top_level_comments[0]
            answer = top_comment.body
            if write_to_qa_files(question, answer, questions_file, answers_file, blacklist):
                question_answer_pairs_count += 1
        # get all comment-reply pairs
        comment_queue = top_level_comments # Seed with top-level
        while comment_queue:
            comment = comment_queue.pop(0)
            comment_queue.extend(comment.replies)
            question = comment.body
            if len(comment.replies) > 0:
                top_reply = comment.replies[0]
                answer = top_reply.body
                if write_to_qa_files(question, answer, questions_file, answers_file, blacklist):
                    question_answer_pairs_count += 1

        total_qa_count += question_answer_pairs_count
    return submission_count, total_qa_count


def main(reddit_uname, reddit_cli_id, reddit_cli_secret, subreddit_name):

    my_cli_id = reddit_cli_id
    my_cli_secret = reddit_cli_secret
    my_user_agent = ''.join(['python:AskMeAboutX:v0.1.0 (by /u/', reddit_uname, ')'])

    questions_file = ''.join([subreddit_name, '-questions.txt'])
    answers_file = ''.join([subreddit_name, '-answers.txt'])

    # get a read-only Reddit instance
    reddit = praw.Reddit(client_id=my_cli_id,
                         client_secret=my_cli_secret,
                         user_agent=my_user_agent)
    print(reddit.read_only)

    # get a subreddit
    subreddit = reddit.subreddit(subreddit_name)

    print(subreddit.display_name)  # Output: redditdev
    print(subreddit.title)         # Output: reddit Development
    # print(subreddit.description)   # Output: A subreddit for discussion of ...

    # TODO: check if questions_file, answers_file already exist, if so delete them

    num_submissions, qa_count = get_question_answer_pairs(subreddit, questions_file, answers_file)
    print(num_submissions, qa_count)

if __name__ == '__main__':
    if len(sys.argv) != 5:
        print('usage: python3 reddit-allpairs.py <reddit username> <reddit OAuth client ID> <reddit OAuth secret> <subreddit name>')
    else:
        reddit_name = sys.argv[1]
        reddit_id = sys.argv[2]
        reddit_secret = sys.argv[3]
        subreddit_name = sys.argv[4]
        main(reddit_name, reddit_id, reddit_secret, subreddit_name)



