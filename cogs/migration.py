from discord.ext import commands
from utils import logger
import motor.motor_asyncio
from environs import Env
from utils.libs.jsondb import JSONDB

db = JSONDB()

env = Env()
env.read_env()

MDB = motor.motor_asyncio.AsyncIOMotorClient(env('MONGODB'))['issuetracking']

log = logger.logger


class Migration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def migrate(self, ctx):
        updated = 0
        inserted = 0
        reports = db.jget("reports", {})
        collection = MDB['Reports']
        for report in reports.items():
            (report_id, report) = report
            reportId = report['report_id']
            found = await collection.find_one({"report_id": reportId})
            if found is not None:
                await collection.replace_one({"report_id": reportId}, report)
                updated += 1
            else:
                await collection.insert_one(report)
                inserted += 1
        print("Reports:")
        print(f"Inserted: {inserted}")
        print(f"Updated: {updated}")


def setup(bot):
    log.info("Loading Migration Cog...")
    bot.add_cog(Migration(bot))
