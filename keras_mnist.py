# ClearML - Keras with Tensorboard example code, automatic logging model and Tensorboard outputs
#
# Train a simple deep NN on the MNIST dataset.
# Then store a model to be served by clearml-serving
import argparse
import os
import tempfile

import numpy as np
import tensorflow as tf
from pathlib import Path
from tensorflow.keras import utils as np_utils
from tensorflow.keras.callbacks import ModelCheckpoint, TensorBoard
from tensorflow.keras.datasets import mnist
from tensorflow.keras.layers import Activation, Dense
from tensorflow.keras.models import Sequential
from tensorflow.keras.optimizers import RMSprop

from clearml import Task


class TensorBoardImage(TensorBoard):
    @staticmethod
    def make_image(tensor):
        from PIL import Image
        import io
        tensor = np.stack((tensor, tensor, tensor), axis=2)
        height, width, channels = tensor.shape
        image = Image.fromarray(tensor)
        output = io.BytesIO()
        image.save(output, format='PNG')
        image_string = output.getvalue()
        output.close()
        return tf.Summary.Image(height=height,
                                width=width,
                                colorspace=channels,
                                encoded_image_string=image_string)

    def on_epoch_end(self, epoch, logs=None):
        if logs is None:
            logs = {}
        super(TensorBoardImage, self).on_epoch_end(epoch, logs)
        images = self.validation_data[0]  # 0 - data; 1 - labels
        img = (255 * images[0].reshape(28, 28)).astype('uint8')

        image = self.make_image(img)
        summary = tf.Summary(value=[tf.Summary.Value(tag='image', image=image)])
        self.writer.add_summary(summary, epoch)


def create_config_pbtxt(model, config_pbtxt_file):
    platform = "tensorflow_savedmodel"
    input_name = model.input_names[0]
    output_name = model.output_names[0]
    input_data_type = "TYPE_FP32"
    output_data_type = "TYPE_FP32"
    input_dims = str(model.input.shape.as_list()).replace("None", "-1")
    output_dims = str(model.output.shape.as_list()).replace("None", "-1")

    config_pbtxt = """
        platform: "%s"
        input [
            {
                name: "%s"
                data_type: %s
                dims: %s
            }
        ]
        output [
            {
                name: "%s"
                data_type: %s
                dims: %s
            }
        ]
    """ % (
        platform,
        input_name, input_data_type, input_dims,
        output_name, output_data_type, output_dims
    )

    with open(config_pbtxt_file, "w") as config_file:
        config_file.write(config_pbtxt)


def main():
    parser = argparse.ArgumentParser(description='Keras MNIST Example - training CNN classification model')
    parser.add_argument('--batch-size', type=int, default=128, help='input batch size for training (default: 128)')
    parser.add_argument('--epochs', type=int, default=1, help='number of epochs to train (default: 6)')
    args = parser.parse_args()

    # the data, shuffled and split between train and test sets
    nb_classes = 10
    (X_train, y_train), (X_test, y_test) = mnist.load_data()

    X_train = X_train.reshape(60000, 784).astype('float32') / 255.
    X_test = X_test.reshape(10000, 784).astype('float32') / 255.
    print(X_train.shape[0], 'train samples')
    print(X_test.shape[0], 'test samples')

    # convert class vectors to binary class matrices
    Y_train = np_utils.to_categorical(y_train, nb_classes)
    Y_test = np_utils.to_categorical(y_test, nb_classes)

    model = Sequential()
    model.add(Dense(512, input_shape=(784,)))
    model.add(Activation('relu'))
    # model.add(Dropout(0.2))
    model.add(Dense(512))
    model.add(Activation('relu'))
    # model.add(Dropout(0.2))
    model.add(Dense(10))
    model.add(Activation('softmax'))

    model2 = Sequential()
    model2.add(Dense(512, input_shape=(784,)))
    model2.add(Activation('relu'))

    model.summary()

    model.compile(
        loss='categorical_crossentropy',
        optimizer=RMSprop(),
        metrics=['accuracy']
    )

    # Connecting ClearML with the current process,
    # from here on everything is logged automatically
    task = Task.init(project_name='examples', task_name='Keras MNIST serve example', output_uri=True)
    task.set_base_docker("tensorflow/tensorflow:2.5.0-gpu")
    task.execute_remotely("v2-gpu")
    # Advanced: setting model class enumeration
    labels = dict(('digit_%d' % i, i) for i in range(10))
    task.set_model_label_enumeration(labels)

    output_folder = os.path.join(tempfile.gettempdir(), 'keras_example_new_temp_now')

    board = TensorBoard(histogram_freq=1, log_dir=output_folder, write_images=False)
    model_store = ModelCheckpoint(filepath=os.path.join(output_folder, 'weight.{epoch}.hdf5'))

    # load previous model, if it is there
    # noinspection PyBroadException
    try:
        model.load_weights(os.path.join(output_folder, 'weight.1.hdf5'))
    except Exception:
        pass

    model.fit(
        X_train, Y_train,
        batch_size=args.batch_size, epochs=args.epochs,
        callbacks=[board, model_store],
        verbose=1, validation_data=(X_test, Y_test)
    )
    score = model.evaluate(X_test, Y_test, verbose=0)

    # store the model in a format that can be served
    model.save('serving_model', include_optimizer=False)

    # create the config.pbtxt for triton to be able to serve the model
    create_config_pbtxt(model=model, config_pbtxt_file='config.pbtxt')
    # store the configuration on the creating Task,
    # this will allow us to skip over manually setting the config.pbtxt for `clearml-serving`
    task.connect_configuration(configuration=Path('config.pbtxt'), name='config.pbtxt')

    print('Test score: {}'.format(score[0]))
    print('Test accuracy: {}'.format(score[1]))


if __name__ == '__main__':
    main()
