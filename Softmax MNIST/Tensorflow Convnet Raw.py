import tensorflow as tf
from image_reader_utils import *
import matplotlib.pyplot as plt
from tensorflow.python.framework import ops

######################################
"""CREATE WRAPPERS FOR CONVOLUTIONAL NETWORK OPERATIONS"""
######################################

def create_placeholders(n_h,n_w,n_c,n_y):

    X = tf.placeholder(tf.float32, shape=[None, n_h, n_w, n_c])
    Y = tf.placeholder(tf.float32, shape=[None, n_y])

    return X,Y

def build_parameters():
    ######################################
    """BUILD FILTERS WITH BIASES"""
    ######################################
    """
    Filters should be of shape height, width, and number of channels with defined total number of filters. 
    e.g. [4,4,3,32] defines a 4x4 filter for a 3 channel input that outputs 32 channels.
    """
    F1 = tf.get_variable('F1', shape=[4, 4, 3, 32], initializer=tf.contrib.layers.xavier_initializer(seed=1))
    fb1 = tf.get_variable('fb1', shape=[32], initializer=tf.zeros_initializer())

    F2 = tf.get_variable('F2', shape=[4, 4, 32, 64], initializer=tf.contrib.layers.xavier_initializer(seed=1))
    fb2 = tf.get_variable('fb2', shape=[64], initializer=tf.zeros_initializer())

    F3 = tf.get_variable('F3', shape=[4, 4, 64, 128], initializer=tf.contrib.layers.xavier_initializer(seed=1))
    fb3 = tf.get_variable('fb3', shape=[128], initializer=tf.zeros_initializer())

    ######################################
    """BUILD WEIGHTS WITH BIASES FOR FULLY CONNECTED LAYERS"""
    ######################################

    b1 = tf.get_variable('b1', shape=[1024, 1], initializer=tf.zeros_initializer())

    W2 = tf.get_variable('W2', shape=[512, 1024], initializer=tf.contrib.layers.xavier_initializer(seed=1))
    b2 = tf.get_variable('b2', shape=[512, 1], initializer=tf.zeros_initializer())

    W3 = tf.get_variable('W3', shape=[10, 512], initializer=tf.contrib.layers.xavier_initializer(seed=1))
    b3 = tf.get_variable('b3', shape=[10, 1], initializer=tf.zeros_initializer())

    ######################################
    """STORE FILTERS AND WEIGHTS """
    ######################################
    parameters = {'F1': F1,
                  'fb1': fb1,
                  'F2': F2,
                  'fb2': fb2,
                  'F3': F3,
                  'fb3': fb3,
                  'b1': b1,
                  'W2': W2,
                  'b2': b2,
                  'W3': W3,
                  'b3': b3}

    return parameters

def conv2d(x, b, filter, strides=1, padding='SAME'):
    x = tf.nn.conv2d(x, filter, strides=[1, strides, strides, 1], padding=padding)
    x = tf.nn.bias_add(x, b)
    x = tf.nn.relu(x)
    return x

def maxpool2d(x, k=2, padding='SAME'):
    x = tf.nn.max_pool(x, ksize=[1, k, k, 1],strides=[1, k, k, 1], padding=padding)
    return x

def dropout(x, prob):
    x = tf.nn.dropout(x, prob)
    return x

def dense(x, W, b):
    x = tf.add(tf.matmul(W, x), b)
    x = tf.nn.relu(x)
    return x

def flatten(x):
    x = tf.keras.layers.Flatten()(x)
    return x

def one_hot_mat(y, n_classes):
    """

    :param y: label vector
    :param n_classes: number of different classes
    :return: one hot tensorflow matrix
    """

    n_c = tf.constant(n_classes, name='n_classes')

    one_hot_mat = tf.one_hot(y, depth=n_c, axis=0)

    sess = tf.Session()

    one_hot = sess.run(one_hot_mat)

    sess.close()

    return one_hot

######################################
"""BUILD CONVNET"""
######################################


def convnet(X, parameters, keep_prob):

    ####FIRST CONVOLUTION LAYER####
    conv1 = conv2d(X, parameters['fb1'], parameters['F1'], strides=1, padding='SAME')
    conv1 = maxpool2d(conv1, k=3)

    ####SECOND CONVOLUTION LAYER####
    conv2 = conv2d(conv1, parameters['fb2'], parameters['F2'], strides=1, padding='SAME')
    conv2 = maxpool2d(conv2, k=3)

    ####THIRD CONVOLUTION LAYER####
    conv3 = conv2d(conv2, parameters['fb3'], parameters['F3'], strides=1, padding='SAME')
    conv3 = maxpool2d(conv3, k=3)

    ####FULLY CONNECTED LAYERS####
    fc1 = flatten(conv3)

    d1= tf.keras.layers.Dense(1024)(fc1)
    d1 = dropout(d1, keep_prob)
    d2 = dense(d1, parameters['W2'], parameters['b2'])
    d2 = dropout(d2, keep_prob)
    out = dense(d2, parameters['W3'], parameters['b3'])

    return out


def model(X_train,Y_train,X_test,Y_test,epochs=15,batch_size=5,learning_rate=0.001):

    ops.reset_default_graph()
    tf.reset_default_graph()
    tf.set_random_seed(123)

    m, n_h, n_w, n_c = X_train.shape #Number of training examples
    n_y = Y_train.shape[1]

    costs = []

    ######################################
    """CREATE PLACEHOLDER FOR GRAPH INPUT"""
    ######################################

    X,Y = create_placeholders(n_h,n_w,n_c,n_y)
    keep_prob = tf.placeholder(tf.float32)

    parameters = build_parameters()

    ######################################
    """BUILD PREDICTIONS AND CHECK PREDICTIONS AND DEFINE OPTIMIZATION"""
    ######################################

    logits = convnet(X, parameters, keep_prob)
    predictions = tf.nn.softmax(logits)

    loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits_v2(logits=logits, labels=Y))

    opt = tf.train.AdamOptimizer(learning_rate=learning_rate).minimize(loss)

    evaluate = tf.equal(tf.argmax(predictions,1), tf.argmax(Y,1))

    accuracy = tf.reduce_mean(tf.cast(evaluate, tf.float32))

    ######################################
    """INITIALIZE TENSORS AND BEGIN TRAINING"""
    ######################################

    tf.reset_default_graph()

    init = tf.global_variables_initializer()

    with tf.Session() as sess:

        sess.run(init)

        shuffler = np.random.permutation(m)
        X_shuffled = X_train[shuffler,:,:,:]
        Y_shuffled = Y_train[shuffler,:]
        print("Shuffled shape: ",X_train.shape)

        for epoch in range(epochs):
            epoch = epoch + 1
            epoch_cost = 0
            mb_costs = []

            total_batches = int(m / batch_size)

            if m % batch_size == 0:
                for batch_num in range(total_batches):
                    X_batch = X_shuffled[batch_num * batch_size:batch_num * batch_size + batch_size,:,:,:]
                    Y_batch = Y_shuffled[batch_num * batch_size:batch_num * batch_size + batch_size,:]

                    _, mb_cost = sess.run([opt, cost], feed_dict={X: X_batch, Y: Y_batch, keep_prob: 0.8})
                    mb_costs.append(mb_cost)

                    epoch_cost += mb_cost / total_batches
                plt.plot(np.squeeze(mb_costs))
                plt.title("Minibatch Costs")
                plt.show()
            else:
                for batch_num in range(total_batches):
                    try:
                        X_batch = X_shuffled[batch_num * batch_size:batch_num * batch_size + batch_size,:,:,:]
                        Y_batch = Y_shuffled[batch_num * batch_size:batch_num * batch_size + batch_size,:]
                    except:
                        try:
                            X_batch = X_shuffled[batch_num * batch_size:batch_num * batch_size + batch_size,:,:,:]
                            Y_batch = Y_shuffled[batch_num * batch_size:batch_num * batch_size + batch_size,:]
                        except:
                            print("Error slicing minibatches")
                    _, mb_cost = sess.run([opt, cost], feed_dict={X: X_batch, Y: Y_batch, keep_prob: 0.8})
                    plt.plot(np.squeeze(mb_costs))
                    plt.title("Minibatch Costs")
                    plt.show()

                    epoch_cost += mb_cost/total_batches
            if (print_cost == True) and (epoch % 5 == 0):
                print("Total Cost at Epoch {epoch}: {cost}".format(epoch=epoch,cost=epoch_cost))
            costs.append(epoch_cost)

        parameters = sess.run(parameters)

        print("Train Accuracy: ", accuracy.eval({X: X_train, Y: Y_train}))
        print("Test Accuracy: ", accuracy.eval({X: X_test, Y: Y_test}))

        return parameters,costs


if __name__ == "__main__":

    X_train = np.load("D:\\Image Data\\Data\\X_train.npy")
    X_test = np.load("D:\\Image Data\\Data\\X_test.npy")
    Y_train = np.load("D:\\Image Data\\Data\\Y_train.npy")
    Y_test = np.load("D:\\Image Data\\Data\\Y_test.npy")

    n_c = len(np.unique(Y_train))

    Y_train = one_hot_mat(Y_train, n_c).T
    Y_test = one_hot_mat(Y_test, n_c).T

    print("Shape of Y: ", Y_train.shape)
    print("Shape of X: ",X_train.shape)

    params, cost = model(X_train, Y_train, X_test, Y_test, epochs=15, batch_size=5, learning_rate=0.001)

    plt.plot(np.squeeze(costs))

    plt.ylabel('cost')
    plt.xlabel('iterations')
    plt.title("Cost per iteration")
    plt.show()

