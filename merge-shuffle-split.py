#!/bin/python3

import sys
import random

def write_list_to_file(input_lst, filename):
    with open(filename, 'a') as f:
        for elem in input_lst:
            f.write(elem)

def main(files_prefix_lst):

    # merge all input files into one for questions, one for answers
    combined_questions = []
    combined_answers = []

    for prefix in files_prefix_lst:
        questions_file = ''.join([prefix, '-questions.txt'])
        with open(questions_file, 'r') as fi:
            combined_questions.extend(fi.readlines())
        answers_file = ''.join([prefix, '-answers.txt'])
        with open(answers_file, 'r') as fi:
            combined_answers.extend(fi.readlines())

    # shuffle
    num_q = len(combined_questions)
    num_a = len(combined_answers)
    if num_q != num_a:
        print("PROBLEM: the number of questions and answers is not equal")
        print('num questions:', num_q)
        print('num answers:', num_a)
    else:
        num_qa = num_q

    # split- 80% train, 10% dev, 10% test
        questions_train_file = 'questions-train.txt'
        questions_dev_file = 'questions-dev.txt'
        questions_test_file = 'questions-test.txt'
        answers_train_file = 'answers-train.txt'
        answers_dev_file = 'answers-dev.txt'
        answers_test_file = 'answers-test.txt'

        index = range(num_qa)
        index_shuffled = random.sample(index, num_qa)
        max_ind_train = int(0.8 * num_qa)
        max_ind_dev = max_ind_train + int((num_qa - max_ind_train)/2)
        print('num lines', num_qa)
        print('80% train, max line train', max_ind_train)
        print('10% dev, max line dev', max_ind_dev)
        print('10% test')
        # print(index)
        # print(index_shuffled)

        combined_questions_shuffled = [combined_questions[i] for i in index_shuffled]
        combined_answers_shuffled = [combined_answers[i] for i in index_shuffled]

        questions_train = combined_questions_shuffled[0:max_ind_train]
        questions_dev = combined_questions_shuffled[max_ind_train:max_ind_dev]
        questions_test = combined_questions_shuffled[max_ind_dev:]
        answers_train = combined_answers_shuffled[0:max_ind_train]
        answers_dev = combined_answers_shuffled[max_ind_train:max_ind_dev]
        answers_test = combined_answers_shuffled[max_ind_dev:]

        write_list_to_file(questions_train, questions_train_file)
        write_list_to_file(questions_dev, questions_dev_file)
        write_list_to_file(questions_test, questions_test_file)
        write_list_to_file(answers_train, answers_train_file)
        write_list_to_file(answers_dev, answers_dev_file)
        write_list_to_file(answers_test, answers_test_file)


if __name__ == '__main__':
    prefixes = sys.argv[1:]
    main(prefixes)
    print("COMPLETE")

