import itertools
import json
import logging
import multiprocessing
import os
from queue import Queue
import re
import shutil
import subprocess
import tempfile
import threading

from bblfsh import BblfshClient
from bblfsh.launcher import ensure_bblfsh_is_running
from bblfsh.github.com.bblfsh.sdk.uast.generated_pb2 import DESCRIPTOR
import Stemmer


class Repo2Base:
    LOG_NAME = None
    NAME_BREAKUP_RE = re.compile(r"[^a-zA-Z]+")
    STEM_THRESHOLD = 6
    MAX_TOKEN_LENGTH = 256
    SIMPLE_IDENTIFIER = DESCRIPTOR.enum_types_by_name["Role"] \
        .values_by_name["SIMPLE_IDENTIFIER"].number + 1
    # FIXME(vmarkovtsev): remove "+1"

    def __init__(self, tempdir=None, linguist=None, log_level=logging.INFO,
                 bblfsh_endpoint=None):
        self._log = logging.getLogger(self.LOG_NAME)
        self._log.setLevel(log_level)
        self._stemmer = Stemmer.Stemmer("english")
        self._stemmer.maxCacheSize = 0
        self._stem_threshold = 6
        self._tempdir = tempdir
        self._linguist = "enry" if linguist is None else linguist
        self._bblfsh = [BblfshClient(bblfsh_endpoint or "0.0.0.0:9432")
                        for _ in range(multiprocessing.cpu_count())]

    def convert_repository(self, url_or_path):
        temp = not os.path.exists(url_or_path)
        if temp:
            target_dir = tempfile.mkdtemp(
                prefix="repo2nbow-", dir=self._tempdir)
            self._log.info("Cloning from %s...", url_or_path)
            try:
                subprocess.check_call(
                    ["git", "clone", "--depth=1", url_or_path, target_dir])
            except Exception as e:
                shutil.rmtree(target_dir)
                raise e from None
        else:
            target_dir = url_or_path
        try:
            self._log.info("Classifying the files...")
            classified = self._classify_files(target_dir)
            self._log.info("Fetching and processing UASTs...")

            def uast_generator():
                queue_in = Queue()
                queue_out = Queue()

                def thread_loop(thread_index):
                    while True:
                        task = queue_in.get()
                        if task is None:
                            break
                        try:
                            filename, language = task

                            # Check if filename is symlink
                            if os.path.islink(filename):
                                filename = os.readlink(filename)

                            uast = self._bblfsh[thread_index].parse_uast(
                                filename, language=language)
                            queue_out.put_nowait(uast)
                        except:
                            self._log.exception(
                                "Error while processing %s.", task)
                            queue_out.put_nowait(None)

                pool = [threading.Thread(target=thread_loop, args=(i,))
                        for i in range(multiprocessing.cpu_count())]
                for thread in pool:
                    thread.start()
                tasks = 0
                for lang, files in classified.items():
                    # FIXME(vmarkovtsev): remove this hardcode when https://github.com/bblfsh/server/issues/28 is resolved
                    lang_list = ("Python", "Java",)
                    if lang not in lang_list:
                        continue
                    for f in files:
                        tasks += 1
                        queue_in.put_nowait((os.path.join(target_dir, f),
                                             lang))
                report_interval = max(1, tasks // 100)
                for _ in pool:
                    queue_in.put_nowait(None)
                while tasks > 0:
                    result = queue_out.get()
                    if result is not None:
                        yield result
                    tasks -= 1
                    if tasks % report_interval == 0:
                        self._log.info("%s pending tasks: %d", url_or_path,
                                       tasks)
                for thread in pool:
                    thread.join()

            return self.convert_uasts(uast_generator())
        finally:
            if temp:
                shutil.rmtree(target_dir)

    def convert_uast(self, uast):
        return self.convert_uasts([uast])

    def convert_uasts(self, uast_generator):
        raise NotImplementedError()

    def _classify_files(self, target_dir):
        target_dir = os.path.abspath(target_dir)
        # FIXME(vmarkovtsev): add --json when we implement https://github.com/src-d/enry/issues/39
        # FIXME(vmarkovtsev): change to check_output() when we fix https://github.com/src-d/enry/issues/40
        bjson = subprocess.run(
            [self._linguist, target_dir],
            stdout=subprocess.PIPE, check=False).stdout
        classified = json.loads(bjson.decode("utf-8"))
        return classified

    def _process_token(self, token):
        for word in self._split(token):
            yield self._stem(word)

    def _stem(self, word):
        if len(word) <= self._stem_threshold:
            return word
        return self._stemmer.stemWord(word)

    @classmethod
    def _split(cls, token):
        token = token.strip()[:cls.MAX_TOKEN_LENGTH]
        prev_p = [""]

        def ret(name):
            r = name.lower()
            if len(name) >= 3:
                yield r
                if prev_p[0]:
                    yield prev_p[0] + r
                    prev_p[0] = ""
            else:
                prev_p[0] = r

        for part in cls.NAME_BREAKUP_RE.split(token):
            if not part:
                continue
            prev = part[0]
            pos = 0
            for i in range(1, len(part)):
                this = part[i]
                if prev.islower() and this.isupper():
                    yield from ret(part[pos:i])
                    pos = i
                elif prev.isupper() and this.islower():
                    if 0 < i - 1 - pos <= 3:
                        yield from ret(part[pos:i - 1])
                        pos = i - 1
                    elif i - 1 > pos:
                        yield from ret(part[pos:i])
                        pos = i
                prev = this
            last = part[pos:]
            if last:
                yield from ret(last)


def ensure_bblfsh_is_running_noexc():
    try:
        ensure_bblfsh_is_running()
    except:
        log = logging.getLogger("bblfsh")
        log.exception("Failed to ensure that the Babelfish server is running.")


def repos2_entry(args, payload_func):
    ensure_bblfsh_is_running_noexc()
    inputs = []

    for i in args.input:
        # check if it's a text file
        if os.path.isfile(i):
            with open(i) as f:
                inputs.extend(l.strip() for l in f)
        else:
            inputs.append(i)

    os.makedirs(args.output, exist_ok=True)

    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        pool.starmap(payload_func, itertools.product(inputs, [args]))
