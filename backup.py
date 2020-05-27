# -*- coding: utf-8 -*-
from typing import Optional, Callable
from os import path, makedirs, listdir
from shutil import rmtree
from datetime import datetime, timedelta
from subprocess import call
import re


def get_backup_time_from_dirname(dirname: str) -> Optional[datetime]:
    matches = re.match(r"^(?P<year>\d{4})-(?P<month>\d{2})-" +
                       r"(?P<day>\d{2})_(?P<hour>\d{2}):(?P<minute>\d{2})$",
                       dirname)
    if matches is None:
        return None
    return datetime(year=int(matches.groupdict()['year']),
                    month=int(matches.groupdict()['month']),
                    day=int(matches.groupdict()['day']),
                    hour=int(matches.groupdict()['hour']),
                    minute=int(matches.groupdict()['minute']))


def find_last_backup_dir(backup_base_dir: str):
    newest_backup_time = datetime(2020, 5, 27, 12, 0)
    newest_backup = "first_backup"
    for d in listdir(backup_base_dir):
        backup_time = get_backup_time_from_dirname(d)
        if backup_time and backup_time > newest_backup_time:
            newest_backup_time = backup_time
            newest_backup = d
    return newest_backup


def keep_one_per(backup_base_dir: str, after: timedelta, check_time_range: Callable[[datetime, datetime], bool]):
    keep_backups = {}
    for d in listdir(backup_base_dir):
        backup_time = get_backup_time_from_dirname(d)
        if backup_time:
            day_already_has_a_backup = False
            for key_time in keep_backups.keys():
                if check_time_range(backup_time, key_time):
                    day_already_has_a_backup = True
                    if key_time < backup_time:
                        del keep_backups[key_time]
                        keep_backups[backup_time] = d
                        break
            if not day_already_has_a_backup:
                keep_backups[backup_time] = d
    for d in listdir(backup_base_dir):
        backup_time = get_backup_time_from_dirname(d)
        if backup_time and backup_time < datetime.now() - after:
            if backup_time not in keep_backups.keys():
                rmtree(d)


def keep_one_per_day(backup_base_dir: str, after_days: int = 3):
    def check_same_day(a: datetime, b: datetime) -> bool:
        return a.year == b.year and a.month == b.month and a.day == b.day
    keep_one_per(backup_base_dir, timedelta(days=after_days), check_same_day)


def keep_one_per_week(backup_base_dir: str, after_days: int = 90):
    def check_same_week(a: datetime, b: datetime) -> bool:
        if a.year != b.year or a.month != b.month:
            return False
        for i in range(5):
            month = datetime(year=a.year, month=a.month, day=1)
            if (month + timedelta(days=i*7) < a < month + timedelta(days=(i+1)*7) and
                    month + timedelta(days=i*7) < b < month + timedelta(days=(i+1)*7)):
                return True
        return False
    keep_one_per(backup_base_dir, timedelta(days=after_days), check_same_week)


def keep_one_per_month(backup_base_dir: str, after_days: int = 120):
    def check_same_month(a: datetime, b: datetime) -> bool:
        return a.year == b.year and a.month == b.month
    keep_one_per(backup_base_dir, timedelta(days=after_days), check_same_month)


def keep_one_per_year(backup_base_dir: str, after_days: int = 730):
    def check_same_year(a: datetime, b: datetime) -> bool:
        return a.year == b.year
    keep_one_per(backup_base_dir, timedelta(days=after_days), check_same_year)


def clean_old_backups(backup_base_dir: str):
    keep_one_per_day(backup_base_dir, 2)
    keep_one_per_month(backup_base_dir, 100)
    keep_one_per_year(backup_base_dir, 730)
    keep_one_per_week(backup_base_dir, 20)


def check_remote_is_online(remote: str) -> bool:
    return call(['ssh', remote.split(':')[0], 'echo', '"' + remote.split(':')[0] + ' is online."']) == 0


def backup(remote: str = "user@serverHostname:/backup/directory",
           dest_dir: str = "../backup-dir"):
    if not check_remote_is_online(remote):
        print("The remote server {} is unreachable. Skipping backup.".format(remote.split(':')[0]))
        return
    now = datetime.now()
    backup_dir = "{:04d}-{:02d}-{:02d}_{:02d}:{:02d}".format(now.year, now.month, now.day, now.hour, now.minute)
    if path.isdir(path.join(dest_dir, backup_dir)):
        print("Error: Backup dir {} already exisits! Aborting.".format(backup_dir))
        return
    makedirs(path.join(dest_dir, backup_dir))
    call(['rsync', '-arlHpXgtPv', '-zz', '--numeric-ids',
          '--link-dest=' + path.abspath(path.join(dest_dir, find_last_backup_dir(dest_dir))),
          remote, path.abspath(path.join(dest_dir, backup_dir))])
    clean_old_backups(dest_dir)


if __name__ == "__main__":
    backup("pina@pinae.net:/home/pina/Dockerprojekte/*", path.join("..", "server-backup"))
