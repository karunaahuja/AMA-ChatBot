
# coding: utf-8
# PRAW: https://praw.readthedocs.io/en/latest/
#! pip install --upgrade pip
#! pip install praw
#! pip install --upgrade praw
#! pip install nltk
# In[44]:

import json
import praw
import logging

# uncomment to turn on logging and debug PRAW requests to Reddit API
# handler = logging.StreamHandler()
# handler.setLevel(logging.DEBUG)
# logger = logging.getLogger('prawcore')
# logger.setLevel(logging.DEBUG)
# logger.addHandler(handler)


# In[45]:

questions_file = 'askscience-questions.txt'
answers_file = 'askscience-answers.txt'


# # Retrieving data using Reddit API and PRAW wrapper

# In[46]:

my_cli_id = 'P3LozozA5KXU4g'
my_cli_secret = 'FYwAshkIUWO0c9KHqbNyuycLVg4'
my_user_agent = 'python:AskMeAboutX:v0.1.0 (by /u/dimro)'


# In[47]:

# get a read-only Reddit instance
reddit = praw.Reddit(client_id=my_cli_id,
                     client_secret=my_cli_secret,
                     user_agent=my_user_agent)
print(reddit.read_only)


# In[48]:

# get a subreddit
# subreddit = reddit.subreddit('askscience')
subreddit = reddit.subreddit('askscience')

print(subreddit.display_name)  # Output: redditdev
print(subreddit.title)         # Output: reddit Development
# print(subreddit.description)   # Output: A subreddit for discussion of ...


# In[49]:

def replace_newlines(content):
    return content.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')


# In[50]:

def truncate(content, limit):
    words_lst = content.split(' ')
    if len(words_lst) > 20:
        return ' '.join(words_lst[0:limit])
    else:
        return content


# In[51]:

def write_to_qa_files(question, answer, questions_file, answers_file, blacklist):
    if question not in blacklist and answer not in blacklist:
        # replace all newlines with space
        question = replace_newlines(question)
        answer = replace_newlines(answer)
        question_trunc = truncate(question, 20)
        answer_trunc = truncate(answer, 20)
        # write question and answer to separate text files, one per line
        with open(questions_file, mode='a') as fq:
            fq.write(question_trunc + '\n')
        with open(answers_file, mode='a') as fa:
            fa.write(answer_trunc + '\n')
        return True
    return False


# In[53]:

def get_question_answer_pairs(subreddit, questions_file, answers_file):
    blacklist = set(['[deleted]', '[removed]'])

    # get submissions in a subreddit
    submission_count = 0
    estimate_data = {} # dict: submission number-> number of question-answer pairs
    # sort by: relevance, hot, top, new, or comments
    total_qa_count = 0
    for submission in subreddit.submissions(start=0):
        submission_count += 1
        if submission_count % 100 == 0:
#             print(submission_count, submission.title, submission.url, ', author:', submission.author)
            print(total_qa_count, submission_count, submission.title)

        submission.comments.replace_more(limit=0)
        top_level_comments = list(submission.comments)
        question_answer_pairs_count = 0
        question = submission.title
        for tl_comment in top_level_comments:
            answer = tl_comment.body
            question_answer_pairs_count += 1
            question = tl_comment.body
            for reply in tl_comment.replies:
                answer = reply.body
                if write_to_qa_files(question, answer, questions_file, answers_file, blacklist):
                    question_answer_pairs_count += 1
        # get all comment-reply pairs
        comment_queue = submission.comments[:]  # Seed with top-level
        while comment_queue:
            comment = comment_queue.pop(0)
            comment_queue.extend(comment.replies)
            question = comment.body
            for reply in comment.replies:
                answer = reply.body
                if write_to_qa_files(question, answer, questions_file, answers_file, blacklist):
                    question_answer_pairs_count += 1

        total_qa_count += question_answer_pairs_count
    return submission_count, total_qa_count


# In[54]:

# science_submissions, science_estimate = get_question_answer_pairs('flair:science', qa_pairs_file)
num_submissions, qa_count = get_question_answer_pairs(subreddit, questions_file, answers_file)
print(num_submissions, qa_count)


# In[ ]:



