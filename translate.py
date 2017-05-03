# Copyright 2015 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

"""Binary for training translation models and decoding from them.

Running this program without --decode will download the WMT corpus into
the directory specified as --data_dir and tokenize it in a very basic way,
and then start training a model saving checkpoints to --train_dir.

Running with --decode starts an interactive loop so you can see how
the current checkpoint translates English sentences into French.

See the following papers for more information on neural translation models.
 * http://arxiv.org/abs/1409.3215
 * http://arxiv.org/abs/1409.0473
 * http://arxiv.org/abs/1412.2007
"""
from __future__ import absolute_import
from __future__ import division
#from __future__ import logging.debug_function

import math
import os
import random
import sys
import time
import logging

import gensim
import language_check

import numpy as np
from six.moves import xrange  # pylint: disable=redefined-builtin
import tensorflow as tf

import data_utils
import seq2seq_model

from itertools import izip

tf.logging.set_verbosity(tf.logging.ERROR)
tf.app.flags.DEFINE_float("learning_rate", 0.5, "Learning rate.")
tf.app.flags.DEFINE_float("learning_rate_decay_factor", 0.99,
                          "Learning rate decays by this much.")
tf.app.flags.DEFINE_float("max_gradient_norm", 5.0,
                          "Clip gradients to this norm.")
tf.app.flags.DEFINE_integer("batch_size", 1,
                            "Batch size to use during training.")
tf.app.flags.DEFINE_integer("size", 1024, "Size of each model layer.")
tf.app.flags.DEFINE_integer("num_layers", 3, "Number of layers in the model.")
tf.app.flags.DEFINE_integer("en_vocab_size", 50000, "Question vocabulary size.")
tf.app.flags.DEFINE_integer("fr_vocab_size", 50000, "Answer vocabulary size.")
tf.app.flags.DEFINE_string("data_dir", "/home/ubuntu/data", "Data directory")
tf.app.flags.DEFINE_string("train_dir", "/home/ubuntu/checkpoints", "Training directory.")
tf.app.flags.DEFINE_integer("max_train_data_size", 0,
                            "Limit on the size of training data (0: no limit).")
tf.app.flags.DEFINE_integer("steps_per_checkpoint", 200,
                            "How many training steps to do per checkpoint.")
tf.app.flags.DEFINE_boolean("decode", False,
                            "Set to True for interactive decoding.")
tf.app.flags.DEFINE_boolean("self_test", False,
                            "Run a self-test if this is set to True.")
tf.app.flags.DEFINE_boolean("use_fp16", False,
                            "Train using fp16 instead of fp32.")

FLAGS = tf.app.flags.FLAGS

# We use a number of buckets and pad to the closest one for efficiency.
# See seq2seq_model.Seq2SeqModel for details of how they work.
_buckets = [(5, 10), (10, 15), (20, 25), (40, 50),(55,65), (70,90) ]

logging.basicConfig(filename='new_3layers_lr_0_1_1024.log',level=logging.DEBUG)
tool = language_check.LanguageTool('en-US')

def read_data(source_path, target_path, max_size=None):
  """Read data from source and target files and put into buckets.

  Args:
    source_path: path to the files with token-ids for the source language.
    target_path: path to the file with token-ids for the target language;
      it must be aligned with the source file: n-th line contains the desired
      output for n-th line from the source_path.
    max_size: maximum number of lines to read, all other will be ignored;
      if 0 or None, data files will be read completely (no limit).

  Returns:
    data_set: a list of length len(_buckets); data_set[n] contains a list of
      (source, target) pairs read from the provided data files that fit
      into the n-th bucket, i.e., such that len(source) < _buckets[n][0] and
      len(target) < _buckets[n][1]; source and target are lists of token-ids.
  """
  data_set = [[] for _ in _buckets]
  with tf.gfile.GFile(source_path, mode="r") as source_file:
    with tf.gfile.GFile(target_path, mode="r") as target_file:
      source, target = source_file.readline(), target_file.readline()
      counter = 0
      while source and target and (not max_size or counter < max_size):
        counter += 1
        if counter % 1000 == 0:
          logging.debug("  reading data line %d" % counter)
          sys.stdout.flush()
        source_ids = [int(x) for x in source.split()]
        target_ids = [int(x) for x in target.split()]
        target_ids.append(data_utils.EOS_ID)
        for bucket_id, (source_size, target_size) in enumerate(_buckets):
          if len(source_ids) < source_size and len(target_ids) < target_size:
            data_set[bucket_id].append([source_ids, target_ids])
            break
        source, target = source_file.readline(), target_file.readline()
  return data_set


def create_model(session, forward_only):
  """Create translation model and initialize or load parameters in session."""
  dtype = tf.float16 if FLAGS.use_fp16 else tf.float32
  # load word2vec model
  #model_embed = gensim.models.KeyedVectors.load_word2vec_format('/home/ubuntu/GoogleNews-vectors-negative300.bin', binary=True)  
  #model_embed = load_model('', binary=True)
  #X = tf.Variable([0.0])
  #logging.debug(type(X)) # numpy.ndarray
  #logging.debug(X.shape) # (vocab_size, embedding_dim)
  # set embeddings
  #place = tf.placeholder(tf.float32, shape=(3000000, 300))
  #X = tf.Variable(place) 
  #embeddings = X.assign(place)
  #embeddings = tf.Variable(tf.random_uniform(X.shape, minval=-0.1, maxval=0.1), trainable=False)
  model = seq2seq_model.Seq2SeqModel(
      FLAGS.en_vocab_size,
      FLAGS.fr_vocab_size,
      _buckets,
      FLAGS.size,
      FLAGS.num_layers,
      FLAGS.max_gradient_norm,
      FLAGS.batch_size,
      FLAGS.learning_rate,
      FLAGS.learning_rate_decay_factor,
      forward_only=forward_only,
      dtype=dtype)
  ckpt = tf.train.get_checkpoint_state(FLAGS.train_dir)
  if ckpt and tf.train.checkpoint_exists(ckpt.model_checkpoint_path):
    logging.debug("Reading model parameters from %s" % ckpt.model_checkpoint_path)
    model.saver.restore(session, ckpt.model_checkpoint_path)
  else:
    logging.debug("Created model with fresh parameters.")
    #init = tf.initialize_all_variables()
    session.run(tf.global_variables_initializer())
    # override inits
   # session.run(init,feed_dict={place: model_embed.syn0} )
  return model


def train():
  """Train a en->fr translation model using WMT data."""
  # Prepare WMT data.
  logging.debug("Preparing WMT data in %s" % FLAGS.data_dir)
  en_train, fr_train, en_dev, fr_dev, _, _ = data_utils.prepare_wmt_data(
      FLAGS.data_dir, FLAGS.en_vocab_size, FLAGS.fr_vocab_size)

  with tf.Session(config=tf.ConfigProto(log_device_placement=True)) as sess:
    # Create model.
    logging.debug("Creating %d layers of %d units." % (FLAGS.num_layers, FLAGS.size))
    model = create_model(sess, False)

    # Read data into buckets and compute their sizes.
    logging.debug("Reading development and training data (limit: %d)."
           % FLAGS.max_train_data_size)
    dev_set = read_data(en_dev, fr_dev)
    logging.debug("Finish reading data")
    train_set = read_data(en_train, fr_train, FLAGS.max_train_data_size)
    train_bucket_sizes = [len(train_set[b]) for b in xrange(len(_buckets))]
    train_total_size = float(sum(train_bucket_sizes))

    # A bucket scale is a list of increasing numbers from 0 to 1 that we'll use
    # to select a bucket. Length of [scale[i], scale[i+1]] is proportional to
    # the size if i-th training bucket, as used later.
    train_buckets_scale = [sum(train_bucket_sizes[:i + 1]) / train_total_size
                           for i in xrange(len(train_bucket_sizes))]

    # This is the training loop.
    step_time, loss = 0.0, 0.0
    current_step = 0
    previous_losses = []
    logging.debug( 'Started training')
    while True:
      # Choose a bucket according to data distribution. We pick a random number
      # in [0, 1] and use the corresponding interval in train_buckets_scale.
      random_number_01 = np.random.random_sample()
      bucket_id = min([i for i in xrange(len(train_buckets_scale))
                       if train_buckets_scale[i] > random_number_01])

      # Get a batch and make a step.
      start_time = time.time()
      encoder_inputs, decoder_inputs, target_weights = model.get_batch(
          train_set, bucket_id)
      _, step_loss, _ = model.step(sess, encoder_inputs, decoder_inputs,
                                   target_weights, bucket_id, False)
      step_time += (time.time() - start_time) / FLAGS.steps_per_checkpoint
      loss += step_loss / FLAGS.steps_per_checkpoint
      current_step += 1
      # Printing perplexity every 10 iterations for plotting
      #if current_step % 10 == 0:
        #perplexity10 = math.exp(float(loss)) if loss < 300 else float("inf")
        #logging.debug("Plot: global step %d learning rate %.4f step-time %.2f perplexity "
         #      "%.2f" % (model.global_step.eval(), model.learning_rate.eval(),
          #               step_time, perplexity10))

      # Once in a while, we save checkpoint, logging.debugstatistics, and run evals.
      if current_step % FLAGS.steps_per_checkpoint == 0:
        # Print statistics for the previous epoch.
        perplexity = math.exp(float(loss)) if loss < 300 else float("inf")
        logging.debug("global step %d learning rate %.4f step-time %.2f perplexity "
               "%.2f" % (model.global_step.eval(), model.learning_rate.eval(),
                         step_time, perplexity))
        # Decrease learning rate if no improvement was seen over last 3 times.
        if len(previous_losses) > 2 and loss > max(previous_losses[-3:]):
          sess.run(model.learning_rate_decay_op)
        previous_losses.append(loss)
        # Save checkpoint and zero timer and loss.
        checkpoint_path = os.path.join(FLAGS.train_dir, "ama.ckpt")
        model.saver.save(sess, checkpoint_path, global_step=model.global_step)
        step_time, loss = 0.0, 0.0
        # Run evals on development set and logging.debugtheir perplexity.
        for bucket_id in xrange(len(_buckets)):
          if len(dev_set[bucket_id]) == 0:
            logging.debug("  eval: empty bucket %d" % (bucket_id))
            continue
          encoder_inputs, decoder_inputs, target_weights = model.get_batch(
              dev_set, bucket_id)
          _, eval_loss, _ = model.step(sess, encoder_inputs, decoder_inputs,
                                       target_weights, bucket_id, True)
          eval_ppx = math.exp(float(eval_loss)) if eval_loss < 300 else float(
              "inf")
          logging.debug("  eval: bucket %d perplexity %.2f" % (bucket_id, eval_ppx))
        sys.stdout.flush()

def decode_test(data_encoder_inputs_file, data_decoder_outputs_file, gen_decoder_outputs_file):
  with tf.Session() as sess:
    # Create model and load parameters.
    model = create_model(sess, True)
    model.batch_size = 1  # We decode one sentence at a time.
    
    # Load vocabularies.
    en_vocab_path = os.path.join(FLAGS.data_dir,
                                 "vocab%d.q" % FLAGS.en_vocab_size)
    fr_vocab_path = os.path.join(FLAGS.data_dir,
                                 "vocab%d.a" % FLAGS.fr_vocab_size)
    en_vocab, _ = data_utils.initialize_vocabulary(en_vocab_path)
    _, rev_fr_vocab = data_utils.initialize_vocabulary(fr_vocab_path)

    sentences_lst = []
    data_response_lst = []
    test_outputs_lst = []

    # Decode from encoder_inputs_file
    with open(data_encoder_inputs_file) as fq, open(data_decoder_outputs_file) as fa:
      for sentence, data_response in izip(fq, fa):
        sentences_lst.append(sentence)
        data_response_lst.append(data_response)

    for j in range(len(sentences_lst)):
      sentence = sentences_lst[j]
      data_response = data_response_lst[j]
      # Get token-ids for the input sentence.
      token_ids = data_utils.sentence_to_token_ids(tf.compat.as_bytes(sentence), en_vocab)
      # Get token ids for output sentence
      token_ids_output = data_utils.sentence_to_token_ids(tf.compat.as_bytes(data_response), en_vocab)

      # Which bucket does it belong to?
      bucket_id = len(_buckets) - 1
      for i, bucket in enumerate(_buckets):
        if bucket[0] >= len(token_ids):
          bucket_id = i
          break
        else:
          logging.warning("Sentence truncated: %s", sentence)
       
      # Get a 1-element batch to feed the sentence to the model.
      encoder_inputs, decoder_inputs, target_weights = model.get_batch(
            {bucket_id: [(token_ids, token_ids_output)]}, bucket_id)

      # Get output logits for the sentence.
      _, test_loss, output_logits = model.step(sess, encoder_inputs, decoder_inputs,
                                       target_weights, bucket_id, True)
      # This is a greedy decoder - outputs are just argmaxes of output_logits.
      outputs = [int(np.argmax(logit, axis=1)) for logit in output_logits]
      # If there is an EOS symbol in outputs, cut them at that point.
      if data_utils.EOS_ID in outputs:
        outputs = outputs[:outputs.index(data_utils.EOS_ID)]
      generated_response = " ".join([tf.compat.as_str(rev_fr_vocab[output]) for output in outputs])
      ppl_test = math.exp(float(test_loss)) if test_loss < 300 else float("inf")
      # correct grammar
      matches = tool.check(generated_response)
      grammar_corrected_response = language_check.correct(generated_response, matches)

#      logging.debug("question:", sentence)
#      logging.debug("response:", generated_response)
#      logging.debug("grammar corrected response: " ,grammar_corrected_response) 
#      logging.debug("ppl_test:", ppl_test)
#      logging.debug("bucket:", bucket_id)
      test_outputs_lst.append([grammar_corrected_response, str(ppl_test), str(bucket_id)])
      if j % 100 == 0: 
        logging.debug(j, "/", len(sentences_lst))
        # log generated response, ppl_test, bucket_id
        with open(gen_decoder_outputs_file, mode='a') as fo:
          for test_output in test_outputs_lst:
            fo.write('|'.join(test_output) + '\n')
        test_outputs_lst = []

    # log generated response, ppl_test, bucket_id
#    with open(gen_decoder_outputs_file, mode='w') as fo:
#      for test_output in test_outputs_lst:
#        fo.write('|'.join(test_output) + '\n')

def decode():
  with tf.Session() as sess:
    # Create model and load parameters.
    model = create_model(sess, True)
    model.batch_size = 1  # We decode one sentence at a time.

    # Load vocabularies.
    en_vocab_path = os.path.join(FLAGS.data_dir,
                                 "vocab%d.q" % FLAGS.en_vocab_size)
    fr_vocab_path = os.path.join(FLAGS.data_dir,
                                 "vocab%d.a" % FLAGS.fr_vocab_size)
    en_vocab, _ = data_utils.initialize_vocabulary(en_vocab_path)
    fr_vocab, rev_fr_vocab = data_utils.initialize_vocabulary(fr_vocab_path)

    # Decode from standard input.
    sys.stdout.write("enter question> ")
    sys.stdout.flush()
    sentence = sys.stdin.readline()
    sys.stdout.write("enter response> ")
    sys.stdout.flush()
    data_response = sys.stdin.readline()
    while sentence:
      # Get token-ids for the input sentence.
      token_ids = data_utils.sentence_to_token_ids(tf.compat.as_bytes(sentence), en_vocab)
      # Get token ids for output sentence
      token_ids_output = data_utils.sentence_to_token_ids(tf.compat.as_bytes(data_response), fr_vocab)
      # Which bucket does it belong to?
      bucket_id = len(_buckets) - 1
      for i, bucket in enumerate(_buckets):
        if bucket[0] >= len(token_ids):
          bucket_id = i
          break
        else:
          logging.warning("Sentence truncated: %s", sentence) 

      # Get a 1-element batch to feed the sentence to the model.
      encoder_inputs, decoder_inputs, target_weights = model.get_batch(
          {bucket_id: [(token_ids, token_ids_output)]}, bucket_id)
      # Get output logits for the sentence.
      _, test_loss, output_logits = model.step(sess, encoder_inputs, decoder_inputs,
                                       target_weights, bucket_id, True)
      # This is a greedy decoder - outputs are just argmaxes of output_logits.
      outputs = [int(np.argmax(logit, axis=1)) for logit in output_logits]
      if data_utils.EOS_ID in outputs:
        outputs = outputs[:outputs.index(data_utils.EOS_ID)]
      generated_response = " ".join([tf.compat.as_str(rev_fr_vocab[output]) for output in outputs]) 
      matches = tool.check(generated_response)
      grammar_corrected_response = language_check.correct(generated_response, matches) 
     # If there is an EOS symbol in outputs, cut them at that point.
      # Print out French sentence corresponding to outputs.
      ppl_test = math.exp(float(test_loss)) if test_loss < 300 else float("inf")
      logging.debug("generated response:", generated_response)
      logging.debug ("grammar corrected response: ", grammar_corrected_response)
      logging.debug("ppl_test:", ppl_test)
      logging.debug("bucket:", bucket_id)

      sys.stdout.write("enter question> ")
      sys.stdout.flush()
      sentence = sys.stdin.readline()
      sys.stdout.write("enter response> ")
      sys.stdout.flush()
      data_response = sys.stdin.readline()


def self_test():
  """Test the translation model."""
  with tf.Session() as sess:
    logging.debug("Self-test for neural translation model.")
    # Create model with vocabularies of 10, 2 small buckets, 2 layers of 32.
    model = seq2seq_model.Seq2SeqModel(10, 10, [(3, 3), (6, 6)], 32, 2,
                                       5.0, 32, 0.3, 0.99, num_samples=8)
    sess.run(tf.global_variables_initializer())

    # Fake data set for both the (3, 3) and (6, 6) bucket.
    data_set = ([([1, 1], [2, 2]), ([3, 3], [4]), ([5], [6])],
                [([1, 1, 1, 1, 1], [2, 2, 2, 2, 2]), ([3, 3, 3], [5, 6])])
    for _ in xrange(5):  # Train the fake model for 5 steps.
      bucket_id = random.choice([0, 1])
      encoder_inputs, decoder_inputs, target_weights = model.get_batch(
          data_set, bucket_id)
      model.step(sess, encoder_inputs, decoder_inputs, target_weights,
                 bucket_id, False)


def main(_):
  if FLAGS.self_test:
    self_test()
  elif FLAGS.decode:
    decode_test('/home/ubuntu/data/test_q.txt', '/home/ubuntu/data/test_a.txt', '/home/ubuntu/data/test_results.txt')
    # decode()
  else:
    train()

if __name__ == "__main__":
  tf.app.run()
