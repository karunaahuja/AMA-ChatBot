#!/bin/python3

import sys
import praw
import string
import os
#import logging

# uncomment to turn on logging and debug PRAW requests to Reddit API
# handler = logging.StreamHandler()
# handler.setLevel(logging.DEBUG)
# logger = logging.getLogger('prawcore')
# logger.setLevel(logging.DEBUG)
# logger.addHandler(handler)

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

def write_to_qa_files(question, answer, questions_file, answers_file, blacklist, trunc_words_limit=None):
    if question not in blacklist and answer not in blacklist:
        # replace all newlines with space
        question = replace_newlines(question)
        answer = replace_newlines(answer)
        if trunc_words_limit is not None:
            question = truncate(question, trunc_words_limit)
            answer = truncate(answer, trunc_words_limit)
        question = normalize(question)
        answer= normalize(answer)
        # write question and answer to separate text files, one per line
        with open(questions_file, mode='a') as fq:
            fq.write(question + '\n')
        with open(answers_file, mode='a') as fa:
            fa.write(answer + '\n')
        return True
    return False

def iama_question_answer_pairs(subreddit, query_str, questions_file, answers_file, trunc_words_limit=None):
    blacklist = set(['[deleted]', '[removed]'])

    # get submissions in a subreddit
    submission_count = 0
    total_qa_count = 0
    # sort by: relevance, hot, top, new, or comments
    submissions = subreddit.search(syntax='lucene', query=query_str, sort='comments', limit=1000)
    while True:
        try:
            submission = next(submissions)
            submission.comments.replace_more(limit=0)
            top_level_comments = list(submission.comments)
        except StopIteration:
            break
        except Exception as e:
            print(e)
            continue
        else:
            submission_count += 1
            if submission_count % 100 == 0:
                print(total_qa_count, submission_count, submission.title)

            submission_author = submission.author
            question_answer_pairs_count = 0

            for tl_comment in top_level_comments:
                question_author = tl_comment.author
                question = tl_comment.body

                # select pairs of comments where the reply author is the submission author (the "expert")
                for reply in tl_comment.replies:
                    answer_author = reply.author
                    if answer_author == submission_author:
                        answer = reply.body
                        if write_to_qa_files(question, answer, questions_file, answers_file, blacklist, trunc_words_limit):
                            question_answer_pairs_count += 1
            total_qa_count += question_answer_pairs_count
    return submission_count, total_qa_count

def get_question_answer_pairs(subreddit, questions_file, answers_file, trunc_words_limit=None):
    blacklist = set(['[deleted]', '[removed]'])

    # get submissions in a subreddit
    submission_count = 0
    total_qa_count = 0
    # get all submissions available
    submissions = subreddit.submissions(start=0)
    while True:
        try:
            submission = next(submissions)
            submission.comments.replace_more(limit=0)
            top_level_comments = list(submission.comments)
            question_top = submission.title
            if len(top_level_comments) > 0:
                top_comment = top_level_comments[0]
                answer_top = top_comment.body
        except StopIteration:
            break
        except Exception as e:
            print(e)
            continue
        else:
            submission_count += 1
            if submission_count % 100 == 0:
                print(total_qa_count, submission_count, submission.title)
            question_answer_pairs_count = 0
            # get pair of submission title, top-voted top-level comment
            if len(top_level_comments) > 0:
                if write_to_qa_files(question_top, answer_top, questions_file, answers_file, blacklist, trunc_words_limit):
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
                    if write_to_qa_files(question, answer, questions_file, answers_file, blacklist, trunc_words_limit):
                        question_answer_pairs_count += 1

            total_qa_count += question_answer_pairs_count

    return submission_count, total_qa_count


def main(reddit_uname, reddit_cli_id, reddit_cli_secret, subreddit_name, trunc_words_limit):

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

    # delete output files if they already exist
    if os.path.isfile(questions_file):
        os.remove(questions_file)
    if os.path.isfile(answers_file):
        os.remove(answers_file)

    if subreddit_name == 'IAma':
        num_submissions_sci, qa_count_sci = iama_question_answer_pairs(subreddit, 'flair:science', questions_file, answers_file, trunc_words_limit)
        num_submissions_tech, qa_count_tech = iama_question_answer_pairs(subreddit, 'flair:science', questions_file, answers_file, trunc_words_limit)
        num_submissions = num_submission_sci + num_submissions_tech
        qa_count = qa_count_sci + qa_count_tech
    else:
        num_submissions, qa_count = get_question_answer_pairs(subreddit, questions_file, answers_file, trunc_words_limit)
    print(num_submissions, qa_count)

if __name__ == '__main__':
    if len(sys.argv) < 5:
        print('usage: python3 reddit-allpairs.py <reddit username> <reddit OAuth client ID> <reddit OAuth secret> <subreddit name> [truncate words limit]')
        sys.exit(1)
    elif len(sys.argv) >= 5:
        reddit_name = sys.argv[1]
        reddit_id = sys.argv[2]
        reddit_secret = sys.argv[3]
        subreddit_name = sys.argv[4]
        trunc_words_limit = None
    if len(sys.argv) >= 6:
        trunc_words_limit = sys.argv[5]
    main(reddit_name, reddit_id, reddit_secret, subreddit_name, trunc_words_limit)

