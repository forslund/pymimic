import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def progress_bar(item, num_items):
    prev_percent = 100*(item-1)//num_items
    percent = 100*item//num_items
    update = prev_percent//5 != percent//5
    if update:
        sys.stdout.write('\r')
        sys.stdout.write("[%-40s] %d%%" % ('='*((2*percent)//5), percent))
        sys.stdout.flush()
    if item == num_items-1:
        sys.stdout.write('\r')
        sys.stdout.write("[%-40s] %d%%" % ('='*(40), 100))
        sys.stdout.write('\n')
        sys.stdout.flush()
