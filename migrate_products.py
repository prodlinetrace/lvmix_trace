#!/usr/bin/env python
#-*- coding: utf-8 -*-
import logging
import datetime
from data_dumper import db
from data_dumper import Product, Status, Operation, Comment

logging.root.setLevel(logging.INFO)

"""
    # prodasync flag values
    # 0 - default
    # 1 - ready to sync - should be set once assembly is complete
    # 2 - sync completed successfully
    # 3 - sync failed.
    # 10 - product is marked as deleted
"""


def get_products(sync_status=None, oldest_date_string="2017-06-29 06:39:38.973000"):
    """
        gets products from DB younger than given date
    """
    if sync_status is None:
        candidates = Product.query.filter(Product.date_added > oldest_date_string).order_by(Product.date_added).all()
    else:
        candidates = Product.query.filter_by(prodasync=sync_status).filter(Product.date_added > oldest_date_string).order_by(Product.date_added).all()
        
    return candidates

def get_older_products(sync_status=None, oldest_date_string="2017-06-29 06:39:38.973000"):
    """
        gets products from DB older than given date
    """
    if sync_status is None:
        candidates = Product.query.filter(Product.date_added < oldest_date_string).order_by(Product.date_added).all()
    else:
        candidates = Product.query.filter_by(prodasync=sync_status).filter(Product.date_added < oldest_date_string).order_by(Product.date_added).all()
        
    return candidates


def delete_product(id, mark_as_deleted=False):
    product = Product.query.get(id)
    comments = Comment.query.filter_by(product_id=product.id)
    statuses = Status.query.filter_by(product_id=product.id)
    operations = Operation.query.filter_by(product_id=product.id)
    logging.info('Product: {product} date: {date} removed with {comments_count} comments, {status_count} statuses and {operations_count} operations.'.format(product=product.id, date=product.date_added, operations_count=operations.count(), status_count=statuses.count(), comments_count=comments.count()))

    for to_remove in comments, statuses, operations:
        for item in to_remove:
            db.session.delete(item)
    if mark_as_deleted is True:
        product.prodasync = 10
    else:
        db.session.delete(product)
    db.session.commit()
    return True

def main():
    logging.info("Starting main app")
    start_time = datetime.datetime.now()
    products = get_older_products(sync_status=None)
    logging.info("Number of elements to process: {0}".format(len(products)))
    for product in products:
        delete_product(product.id)
    end_time = datetime.datetime.now()
    logging.info("Program finished in: {time}".format(time = end_time - start_time))


if __name__ == "__main__":
    main()