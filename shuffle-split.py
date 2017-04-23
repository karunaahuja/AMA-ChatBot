#!/home/ubuntu/downloads/bin/python3

import random

root = 'science-technology'
all_questions_file = ''.join([root, '-questions.txt'])
all_answers_file = ''.join([root, '-answers.txt'])

all_questions = []
all_answers = []

def read_file_to_list(filename, dest_lst):
  count = 0
  with open(filename, mode='r') as f:
    for line in f.readlines():
      dest_lst.append(line)
      count += 1
  return count

def write_list_to_file(filename, src_lst):
  with open(filename, mode='w') as f:
    for elem in src_lst:
      f.write(elem)

num_q = read_file_to_list(all_questions_file, all_questions)
num_a = read_file_to_list(all_answers_file, all_answers)
if len(all_questions) != len(all_answers):
  print("PROBLEM: the number of questions and answers is not equal")
  print('num questions:', len(all_questions))
  print('num answers:', len(all_answers))
else:
  num_pairs = len(all_questions)
  # shuffle
  indices = range(num_pairs)
  shuf_ind = random.sample(indices, len(indices))
  shuf_q = [all_questions[i] for i in shuf_ind]
  shuf_a = [all_answers[i] for i in shuf_ind]

  # split - 80% training, 10% validation, 10% test/dev
  max_ind_train = int(0.8 * num_pairs)
  questions_train = shuf_q[0:max_ind_train]
  answers_train = shuf_a[0:max_ind_train]
  questions_train_file = ''.join([root, '-questions-train.txt'])
  answers_train_file = ''.join([root, '-answers-train.txt'])
  write_list_to_file(questions_train_file, questions_train)
  write_list_to_file(answers_train_file, answers_train)

  max_ind_val = max_ind_train + int((num_pairs - max_ind_train)/2)
  questions_val = shuf_q[max_ind_train:max_ind_val]
  answers_val = shuf_a[max_ind_train:max_ind_val]
  questions_val_file = ''.join([root, '-questions-val.txt'])
  answers_val_file = ''.join([root, '-answers-val.txt'])
  write_list_to_file(questions_val_file, questions_val)
  write_list_to_file(answers_val_file, answers_val)

  questions_dev = shuf_q[max_ind_val:]
  answers_dev = shuf_q[max_ind_val:]
  questions_dev_file = ''.join([root, '-questions-dev.txt'])
  answers_dev_file = ''.join([root, '-answers-dev.txt'])
  write_list_to_file(questions_dev_file, questions_dev)
  write_list_to_file(answers_dev_file, answers_dev)
