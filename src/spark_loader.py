import sys
import os
import time
import glob
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType
from pyspark.sql.functions import col, lit, current_timestamp, struct, monotonically_increasing_id

os.environ["HADOOP_HOME"] = "C:\\hadoop"

java_possible_paths = (
    glob.glob("C:\\Program Files\\Eclipse Adoptium\\jdk-11*") + 
    glob.glob("C:\\Program Files\\Java\\jdk-11*") +
    glob.glob("C:\\Program Files (x86)\\Eclipse Adoptium\\jdk-11*") +
    glob.glob("C:\\Program Files (x86)\\Java\\jdk-11*")
)

if java_possible_paths:
    os.environ["JAVA_HOME"] = java_possible_paths[0]

if "JDK_JAVA_OPTIONS" in os.environ:
    del os.environ["JDK_JAVA_OPTIONS"]

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.settings import MONGO_URI, DATABASE_NAME

def run_spark_pipeline(file_path, run_id):
    print("=" * 60)
    print(f"🚀 بدء المعالجة المتوازية (PySpark) للملف الكبير: {file_path}")
    start_time = time.time()
    
    spark = SparkSession.builder \
        .appName("HybridDataPipeline_SparkELT") \
        .config("spark.mongodb.write.connection.uri", f"{MONGO_URI}{DATABASE_NAME}.orders_raw") \
        .config("spark.jars.packages", "org.mongodb.spark:mongo-spark-connector_2.12:10.4.0") \
        .getOrCreate()
        
    schema = StructType([
        StructField("\ufefforder_id", StringType(), True),
        StructField("order_date", StringType(), True),
        StructField("status", StringType(), True),
        StructField("customer_id", StringType(), True),
        StructField("customer_name", StringType(), True),
        StructField("customer_phone", StringType(), True),
        StructField("customer_email", StringType(), True),
        StructField("city", StringType(), True),
        StructField("district", StringType(), True),
        StructField("delivery_type", StringType(), True),
        StructField("delivery_cost", StringType(), True),
        StructField("payment_method", StringType(), True),
        StructField("payment_status", StringType(), True),
        StructField("payment_amount", StringType(), True),
        StructField("currency", StringType(), True),
        StructField("total_amount", StringType(), True),
        StructField("items_json", StringType(), True)
    ])

    try:
        # الحل المتوازن: حماية JSON من التمزق مع استعادة المعالجة المتوازية السريعة
        df = spark.read \
            .option("header", "true") \
            .option("quote", '"') \
            .option("escape", '"') \
            .schema(schema) \
            .csv(file_path)

        num_partitions = df.rdd.getNumPartitions()
        raw_columns = [col(c) for c in df.columns]
        
        df_elt = df.withColumn("run_id", lit(run_id)) \
                   .withColumn("source_file", lit(os.path.basename(file_path))) \
                   .withColumn("source_row_number", monotonically_increasing_id()) \
                   .withColumn("ingested_at", current_timestamp()) \
                   .withColumn("engine_used", lit("pyspark")) \
                   .withColumn("raw_record", struct(*raw_columns))
                   
        df_final = df_elt.select("run_id", "source_file", "source_row_number", "ingested_at", "engine_used", "raw_record")
        
        print("⏳ جاري الكتابة المتوازية إلى MongoDB باستخدام Spark Connector المباشر...")
        df_final.write.format("mongodb").mode("append").save()
        
        print("✅ اكتمل التحميل بنجاح تام!")
        
    except Exception as e:
        print(f"❌ حدث خطأ: {e}")
    finally:
        time.sleep(5)
        spark.stop()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="محرك التحميل عبر PySpark")
    parser.add_argument("--input", required=True)
    parser.add_argument("--run_id", default="spark_run_001")
    args = parser.parse_args()
    run_spark_pipeline(args.input, args.run_id)