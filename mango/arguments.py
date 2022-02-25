# # ⚠ Warning
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
# LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN
# NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# [🥭 Mango Markets](https://mango.markets/) support is available at:
#   [Docs](https://docs.mango.markets/)
#   [Discord](https://discord.gg/67jySBhxrg)
#   [Twitter](https://twitter.com/mangomarkets)
#   [Github](https://github.com/blockworks-foundation)
#   [Email](mailto:hello@blockworks.foundation)

import argparse
import logging
import os
import sys
import typing


from .constants import WARNING_DISCLAIMER_TEXT, version
from .output import OutputFormat, output_formatter


# # 🥭 setup_logging
#
# This function sets up logging for mango-explorer commands. It's optional when running
# your own programs, but calling this allows you to have a simple, consistent approach.
#
def setup_logging(log_level: int, suppress_timestamp: bool) -> None:
    log_record_format: str = "%(asctime)s %(level_emoji)s %(name)-12.12s %(message)s"
    if suppress_timestamp:
        log_record_format = "%(level_emoji)s %(name)-12.12s %(message)s"

    # Make logging a little more verbose than the default.
    logging.basicConfig(
        level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S", format=log_record_format
    )

    # Stop libraries outputting lots of information unless it's a warning or worse.
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("solanaweb3").setLevel(logging.WARNING)

    default_log_record_factory: typing.Callable[
        ..., logging.LogRecord
    ] = logging.getLogRecordFactory()
    log_levels: typing.Dict[int, str] = {
        logging.CRITICAL: "🛑",
        logging.ERROR: "🚨",
        logging.WARNING: "⚠",
        logging.INFO: "ⓘ",
        logging.DEBUG: "🐛",
    }

    def _emojified_record_factory(
        *args: typing.Any, **kwargs: typing.Any
    ) -> logging.LogRecord:
        record = default_log_record_factory(*args, **kwargs)
        # Here's where we add our own format keywords.
        setattr(record, "level_emoji", log_levels[record.levelno])
        return record

    logging.setLogRecordFactory(_emojified_record_factory)

    logging.getLogger().setLevel(log_level)


# # 🥭 parse_args
#
# This function parses CLI arguments and sets up common logging for all commands.
#
def parse_args(
    parser: argparse.ArgumentParser, logging_default: int = logging.INFO
) -> argparse.Namespace:
    parser.add_argument(
        "--log-level",
        default=logging_default,
        type=lambda level: typing.cast(object, getattr(logging, level)),
        help="level of verbosity to log (possible values: DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    parser.add_argument(
        "--log-suppress-timestamp",
        default=False,
        action="store_true",
        help="Suppress timestamp in log output (useful for systems that supply their own timestamp on log messages)",
    )
    parser.add_argument(
        "--output-format",
        type=OutputFormat,
        default=OutputFormat.TEXT,
        choices=list(OutputFormat),
        help="output format - can be TEXT (the default) or JSON",
    )

    args: argparse.Namespace = parser.parse_args()
    output_formatter.format = args.output_format

    setup_logging(args.log_level, args.log_suppress_timestamp)

    if not os.environ.get("MANGO_SKIP_DISCLAIMER"):
        logging.warning(WARNING_DISCLAIMER_TEXT)

    if logging.getLogger().isEnabledFor(logging.DEBUG):
        all_arguments: typing.List[str] = []
        for arg in vars(args):
            all_arguments += [f"    --{arg} {getattr(args, arg)}"]
        all_arguments.sort()
        all_arguments_rendered = "\n".join(all_arguments)
        logging.debug(
            f"{os.path.basename(sys.argv[0])} arguments:\n{all_arguments_rendered}"
        )

        logging.debug(f"Version: {version()}")

    return args
