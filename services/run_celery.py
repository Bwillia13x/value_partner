#!/usr/bin/env python3
"""
Script to run Celery worker and beat scheduler for the Value Partner platform.

Usage:
    # Start worker only
    python run_celery.py worker
    
    # Start beat scheduler only
    python run_celery.py beat
    
    # Start both worker and beat in separate processes
    python run_celery.py
    
    # Start with concurrency and log level options
    python run_celery.py --concurrency=4 --loglevel=info
"""
import os
import subprocess
import multiprocessing
import argparse
from pathlib import Path

def run_worker(concurrency=None, loglevel="info", logfile=None):
    """Start Celery worker"""
    cmd = [
        "celery",
        "-A", "services.app.tasks.celery_app",
        "worker",
        f"--loglevel={loglevel}",
        "--without-heartbeat",
        "--without-gossip",
        "--without-mingle",
        "--pool=prefork",
        "--autoscale=10,3",
    ]
    
    if concurrency:
        cmd.extend(["--concurrency", str(concurrency)])
    
    if logfile:
        cmd.extend(["--logfile", str(logfile)])
    
    print(f"Starting Celery worker with command: {' '.join(cmd)}")
    subprocess.call(cmd)

def run_beat(loglevel="info", logfile=None):
    """Start Celery beat scheduler"""
    # Create beat schedule directory if it doesn't exist
    beat_schedule_dir = Path("var/celery/beat-schedule")
    beat_schedule_dir.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "celery",
        "-A", "services.app.tasks.celery_app",
        "beat",
        f"--loglevel={loglevel}",
        "--scheduler=celery.beat.PersistentScheduler",
        f"--schedule={beat_schedule_dir}/celerybeat-schedule",
    ]
    
    if logfile:
        cmd.extend(["--logfile", str(logfile)])
    
    print(f"Starting Celery beat with command: {' '.join(cmd)}")
    subprocess.call(cmd)

def main():
    parser = argparse.ArgumentParser(description="Run Celery worker and beat")
    parser.add_argument(
        "command", 
        nargs="?",
        default="all",
        choices=["all", "worker", "beat"],
        help="Which service to run (default: all)"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=multiprocessing.cpu_count(),
        help=f"Number of worker processes (default: {multiprocessing.cpu_count()})"
    )
    parser.add_argument(
        "--loglevel",
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Logging level (default: info)"
    )
    parser.add_argument(
        "--logdir",
        default="logs",
        help="Directory to store log files (default: logs/)"
    )
    
    args = parser.parse_args()
    
    # Create log directory if it doesn't exist
    log_dir = Path(args.logdir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Set environment variables
    os.environ.setdefault("CELERY_CONFIG_MODULE", "services.app.tasks.config")
    
    if args.command == "all":
        # Start worker in a separate process
        worker_process = multiprocessing.Process(
            target=run_worker,
            kwargs={
                "concurrency": args.concurrency,
                "loglevel": args.loglevel,
                "logfile": log_dir / "celery-worker.log"
            }
        )
        worker_process.start()
        
        # Start beat in the main process
        run_beat(
            loglevel=args.loglevel,
            logfile=log_dir / "celery-beat.log"
        )
        
        # If we get here, beat was terminated
        worker_process.terminate()
        worker_process.join()
        
    elif args.command == "worker":
        run_worker(
            concurrency=args.concurrency,
            loglevel=args.loglevel,
            logfile=log_dir / "celery-worker.log"
        )
    elif args.command == "beat":
        run_beat(
            loglevel=args.loglevel,
            logfile=log_dir / "celery-beat.log"
        )

if __name__ == "__main__":
    main()
