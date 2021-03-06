#!/usr/bin/env python
"""
coding=utf-8

Code Template

"""
import cPickle
import logging
import os

import numpy
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import Imputer, StandardScaler
from sklearn.svm import SVC
from sklearn_pandas import DataFrameMapper, GridSearchCV

import lib


def main():
    """
    Run a pipeline which:

     - Extracts the titanic data set
     - Performs some (light) feature extraction
     - Grid searches a pipeline
     - Loads the results for down stream use

    :return: None
    :rtype: None
    """
    logging.basicConfig(level=logging.DEBUG)

    # Extract
    observations = extract()
    train, test = transform(observations)
    train, test, transformation_pipeline, trained_model = model(train, test)
    load(train, test, transformation_pipeline, trained_model)


def extract():
    """
    Extract the data set from upstream

    :return:
    """
    logging.info('Begin extract')

    # Load the data set
    observations = lib.load_titanic()

    # Subset observation for speedier test iterations
    if lib.get_conf('test_run'):
        logging.warn('test_run is set to True. Subsetting to a much smaller data set for testing purposes.')
        observations = observations.sample(100)
        observations = observations.reset_index()

    lib.archive_dataset_schemas('extract', locals(), globals())
    logging.info('End extract')
    return observations


def transform(observations):
    """
    Perform light feature transformation, ahead of feature transformation pipeline

    :param observations:
    :return:
    """
    logging.info('Begin transform')

    # Convert the gender column to a male or not column
    observations['male'] = observations['sex'] == 'male'

    # Get the honorific (e.g. `Mr.` from `,Mr. Henry Jr Sutehall`)
    observations['honorific'] = observations['name'].apply(lambda x: str(x).split()[0])
    train, test = train_test_split(observations, test_size=0.2)

    lib.archive_dataset_schemas('transform', locals(), globals())
    logging.info('End transform')
    return train, test


def model(train, test):
    """
    Create a pipeline and train a grid searched model

    :param train:
    :param test:
    :return:
    """

    logging.info('Begin model')

    mapper = DataFrameMapper([
        ('honorific', [CountVectorizer(vocabulary=lib.HONORIFIC_VOCABULARY)]),
        (['pclass'], [Imputer(), StandardScaler()]),
        (['male'], [Imputer(), StandardScaler()]),
        (['siblings_spouses_aboard'], [Imputer(), StandardScaler()]),
        (['parents_children_aboard'], [Imputer(), StandardScaler()]),
        (['fare'], [Imputer(), StandardScaler()]),
    ])
    transformation_pipeline = Pipeline([
        ('featureizer', mapper),
        ('svc', SVC())
    ])

    param_grid = {'svc__gamma': numpy.logspace(-9, 3, 1),
                  'svc__C': numpy.logspace(-2, 10, 1),
                  'svc__kernel': ['linear', 'poly', 'rbf', 'sigmoid'],
                  'svc__degree': range(2, 8)}

    trained_model = GridSearchCV(transformation_pipeline, param_grid=param_grid, scoring='accuracy', cv=2, n_jobs=-1)
    logging.info('Training model')
    trained_model.fit(train.copy(), y=train['survived'])

    # Set prediction
    for data_set in [train, test]:
        data_set['pred'] = trained_model.predict(data_set)

    lib.archive_dataset_schemas('model', locals(), globals())
    logging.info('End model')
    return train, test, transformation_pipeline, trained_model


def load(train, test, transformation_pipeline, trained_model):
    """
    Load all assets for downstream use

    :param train:
    :param test:
    :param transformation_pipeline:
    :param trained_model:
    :return:
    """
    logging.info('Begin load')

    # Serialize train
    train_path = os.path.join(lib.get_batch_output_folder(), 'train.csv')
    logging.info('Saving train to path: {}'.format(train_path))
    train.to_csv(train_path, index=False)

    # Serialize test
    test_path = os.path.join(lib.get_batch_output_folder(), 'test.csv')
    logging.info('Saving test to path: {}'.format(train_path))
    test.to_csv(test_path, index=False)

    # Serialize transformation_pipeline
    if transformation_pipeline is not None:
        transformation_pipeline_path = os.path.join(lib.get_batch_output_folder(), 'transformation_pipeline.pkl')
        logging.info('Saving transformation_pipeline to path: {}'.format(transformation_pipeline_path))
        cPickle.dump(transformation_pipeline, open(transformation_pipeline_path, 'w+'))

    # Serialize trained_model
    if trained_model is not None:
        # Serialize trained_model
        trained_model_path = os.path.join(lib.get_batch_output_folder(), 'trained_model.pkl')
        logging.info('Saving trained_model to path: {}'.format(trained_model_path))
        cPickle.dump(trained_model, open(trained_model_path, 'w+'))

        # Capture model results
        print trained_model.cv_results_

    lib.archive_dataset_schemas('load', locals(), globals())
    logging.info('End load')
    pass


# Main section
if __name__ == '__main__':
    main()
