#!/bin/python3

import sys
import random

def read_line_from_file(filename, lineno):
    with open(filename, 'r') as fo:
        for i, line in enumerate(fo):
            if i == lineno:
                return line

def main(files_prefix_lst):

    # merge all input files into one for questions, one for answers
    combined_questions_file = 'combined_questions.txt'
    combined_answers_file = 'combined_answers.txt'

    with open(combined_questions_file, 'w') as fo:
        for prefix in files_prefix_lst:
            questions_file = ''.join([prefix, '-questions.txt'])
            with open(questions_file, 'r') as fi:
                for line in fi.readlines():
                    fo.write(line)
    with open(combined_answers_file, 'w') as fo:
        for prefix in files_prefix_lst:
            answers_file = ''.join([prefix, '-answers.txt'])
            with open(answers_file, 'r') as fi:
                for line in fi.readlines():
                    fo.write(line)

    # shuffle
    num_lines_q = sum(1 for line in open(combined_questions_file))
    num_lines_a = sum(1 for line in open(combined_answers_file))
    if num_lines_q != num_lines_a:
        print("PROBLEM: the number of questions and answers is not equal")
        print('num questions:', num_lines_q)
        print('num answers:', num_lines_a)
    else:
        num_lines = num_lines_q
        line_nums = range(num_lines)

    # split- 80% train, 10% dev, 10% test
        questions_train_file = 'questions-train.txt'
        questions_dev_file = 'questions-dev.txt'
        questions_test_file = 'questions-test.txt'
        answers_train_file = 'answers-train.txt'
        answers_dev_file = 'answers-dev.txt'
        answers_test_file = 'answers-test.txt'

        line_nums_shuffled = random.sample(line_nums, len(line_nums))
        max_line_train = int(0.8 * num_lines)
        max_line_dev = max_line_train + int((num_lines - max_line_train)/2)
        print('num lines', num_lines)
        print('80% train, max line train', max_line_train)
        print('10% dev, max line dev', max_line_dev)
        print('10% test')
        print(line_nums)
        print(line_nums_shuffled)

        count = 0
        for line_num in line_nums_shuffled:
            if count < max_line_train:
                questions_file = questions_train_file
                answers_file = answers_train_file
            elif count < max_line_dev:
                questions_file = questions_dev_file
                answers_file = answers_dev_file
            else:
                questions_file = questions_test_file
                answers_file = answers_test_file
            with open(questions_file, 'a') as fo:
                fo.write(read_line_from_file(combined_questions_file, line_num))
            with open(answers_file, 'a') as fo:
                fo.write(read_line_from_file(combined_answers_file, line_num))
            count += 1

if __name__ == '__main__':
    prefixes = sys.argv[1:]
    main(prefixes)
    print("COMPLETE")

