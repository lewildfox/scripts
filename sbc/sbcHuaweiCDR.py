#!/usr/bin/env python
"""
Huawei CDR Collector - Multi-Server
Author: arif.munandar@telin.co.id
Version: 2.2 - December 2024
- Refactored for better maintainability
- Fixed file size buildup in download tracker
- Added multi-server support (SG and HK)
- Replaced pysftp with paramiko for compatibility
- Improved error handling and logging
"""

import paramiko
import os
import logging
import pwd
import grp
import stat
from pathlib import Path

# Server Configurations
SERVERS = {
    'SG': {
        'host': '202.93.235.116',
        'username': 'Telin',
        'password': 'Kalibata@123',
        'remote_path': '/var/igwb/backsave/Second/AP1/IBCF-CDR',
        'download_dir': '/home/cdr/huawei/SG',
        'tracker_file': '/home/cdr/tmp/downloaded_files_sg.txt'
    },
    'HK': {
        'host': '202.93.234.116',
        'username': 'Telin',
        'password': 'Kalibata@123',
        'remote_path': '/var/igwb/backsave/Second/AP1/IBCF-CDR',
        'download_dir': '/home/cdr/huawei/HK',
        'tracker_file': '/home/cdr/tmp/downloaded_files_hk.txt'
    }
}

# Global Configuration
GLOBAL_CONFIG = {
    'tmp_dir': '/home/cdr/tmp',
    'max_tracker_entries': 10000,  # Prevent unlimited growth
    'target_user': 'cdr',
    'target_group': 'cdr',
    'file_permissions': 0o644,
    'dir_permissions': 0o755,
    'ssh_timeout': 30
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(server)s] %(message)s'
)
logger = logging.getLogger(__name__)


class ServerAdapter(logging.LoggerAdapter):
    """Logger adapter to include server name in logs."""
    def process(self, msg, kwargs):
        return msg, {**kwargs, 'extra': self.extra}


class SFTPConnection:
    """Context manager for SFTP connections using paramiko."""
    
    def __init__(self, host, username, password, timeout=30):
        self.host = host
        self.username = username
        self.password = password
        self.timeout = timeout
        self.ssh_client = None
        self.sftp_client = None
    
    def __enter__(self):
        """Establish SSH and SFTP connection."""
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        self.ssh_client.connect(
            hostname=self.host,
            username=self.username,
            password=self.password,
            timeout=self.timeout,
            allow_agent=False,
            look_for_keys=False
        )
        
        self.sftp_client = self.ssh_client.open_sftp()
        return self.sftp_client
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close SFTP and SSH connections."""
        if self.sftp_client:
            self.sftp_client.close()
        if self.ssh_client:
            self.ssh_client.close()


def set_file_ownership(filepath):
    """Set file ownership to target user/group."""
    try:
        uid = pwd.getpwnam(GLOBAL_CONFIG['target_user']).pw_uid
        gid = grp.getgrnam(GLOBAL_CONFIG['target_group']).gr_gid
        #os.chown(filepath, uid, gid)
        os.chown(filepath, -1, gid)   # group only
        os.chmod(filepath, GLOBAL_CONFIG['file_permissions'])
    except (KeyError, PermissionError) as e:
        logger.warning(f"Cannot set ownership for {filepath}: {e}", extra={'server': 'SYSTEM'})


def ensure_directory_with_permissions(directory):
    """Create directory with proper ownership if it doesn't exist."""
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        try:
            uid = pwd.getpwnam(GLOBAL_CONFIG['target_user']).pw_uid
            gid = grp.getgrnam(GLOBAL_CONFIG['target_group']).gr_gid
            os.chown(directory, uid, gid)
            os.chmod(directory, GLOBAL_CONFIG['dir_permissions'])
            logger.info(f"Created directory with proper ownership: {directory}", extra={'server': 'SYSTEM'})
        except (KeyError, PermissionError) as e:
            logger.warning(f"Cannot set directory ownership for {directory}: {e}", extra={'server': 'SYSTEM'})


def load_downloaded_files(tracker_file):
    """Load set of previously downloaded files from tracker."""
    tracker = Path(tracker_file)
    if not tracker.exists():
        return set()
    
    with open(tracker_file, 'r') as f:
        return set(line.strip() for line in f if line.strip())


def save_downloaded_files(tracker_file, files):
    """Save downloaded files list, keeping only recent entries."""
    # Keep only the most recent entries to prevent buildup
    files_list = sorted(files)[-GLOBAL_CONFIG['max_tracker_entries']:]
    
    with open(tracker_file, 'w') as f:
        f.write('\n'.join(files_list) + '\n')
    
    set_file_ownership(tracker_file)


def get_remote_file_list(server_config, server_log):
    """Retrieve list of files from remote SFTP server."""
    try:
        with SFTPConnection(
            host=server_config['host'],
            username=server_config['username'],
            password=server_config['password'],
            timeout=GLOBAL_CONFIG['ssh_timeout']
        ) as sftp:
            # Change to remote directory
            sftp.chdir(server_config['remote_path'])
            
            # List only regular files (not directories)
            all_items = sftp.listdir_attr()
            files = [item.filename for item in all_items if stat.S_ISREG(item.st_mode)]
            
            server_log.info(f"Retrieved {len(files)} files from remote server")
            return set(files)
    except Exception as e:
        server_log.error(f"Failed to connect to remote server: {e}")
        raise


def find_new_files(remote_files, downloaded_files, server_log):
    """Identify files that haven't been downloaded yet."""
    new_files = remote_files - downloaded_files
    server_log.info(f"Found {len(new_files)} new files to download")
    return sorted(new_files)


def download_files(server_config, file_list, server_log):
    """Download new files from remote server."""
    if not file_list:
        server_log.info("No new files to download")
        return []
    
    downloaded = []
    
    # Ensure download directory exists with proper permissions
    ensure_directory_with_permissions(server_config['download_dir'])
    
    try:
        with SFTPConnection(
            host=server_config['host'],
            username=server_config['username'],
            password=server_config['password'],
            timeout=GLOBAL_CONFIG['ssh_timeout']
        ) as sftp:
            # Change to remote directory
            sftp.chdir(server_config['remote_path'])
            
            for filename in file_list:
                try:
                    local_path = os.path.join(server_config['download_dir'], filename)
                    
                    # Download file
                    sftp.get(filename, local_path)
                    
                    # Preserve modification time
                    remote_attrs = sftp.stat(filename)
                    os.utime(local_path, (remote_attrs.st_atime, remote_attrs.st_mtime))
                    
                    # Set ownership
                    set_file_ownership(local_path)
                    
                    server_log.info(f"Downloaded: {filename}")
                    downloaded.append(filename)
                    
                except Exception as e:
                    server_log.error(f"Failed to download {filename}: {e}")
                    
    except Exception as e:
        server_log.error(f"Download session failed: {e}")
        raise
    
    return downloaded


def process_server(server_name, server_config):
    """Process downloads for a single server."""
    server_log = ServerAdapter(logger, {'server': server_name})
    
    try:
        server_log.info(f"Starting CDR collection from {server_config['host']}")
        
        # Load tracking data
        downloaded_files = load_downloaded_files(server_config['tracker_file'])
        server_log.info(f"Loaded {len(downloaded_files)} previously downloaded files")
        
        # Get remote file list
        remote_files = get_remote_file_list(server_config, server_log)
        
        # Find new files
        new_files = find_new_files(remote_files, downloaded_files, server_log)
        
        # Download new files
        if new_files:
            successfully_downloaded = download_files(server_config, new_files, server_log)
            
            # Update tracker with all known files (old + new)
            # Only keep files that still exist on remote server
            updated_tracker = remote_files & (downloaded_files | set(successfully_downloaded))
            save_downloaded_files(server_config['tracker_file'], updated_tracker)
            
            server_log.info(f"Successfully downloaded {len(successfully_downloaded)} files")
            return {
                'server': server_name,
                'status': 'success',
                'downloaded': len(successfully_downloaded),
                'total_tracked': len(updated_tracker)
            }
        else:
            server_log.info("No new files found on remote server")
            return {
                'server': server_name,
                'status': 'success',
                'downloaded': 0,
                'total_tracked': len(downloaded_files)
            }
            
    except Exception as e:
        server_log.error(f"Server processing failed: {e}")
        return {
            'server': server_name,
            'status': 'failed',
            'error': str(e)
        }


def cleanup_old_tmp_files():
    """Remove temporary processing files (optional maintenance)."""
    tmp_files = ['list.txt', 'result.txt', 'unduh.txt', 'masterlist.txt']
    for fname in tmp_files:
        path = os.path.join(GLOBAL_CONFIG['tmp_dir'], fname)
        if os.path.exists(path):
            try:
                os.remove(path)
                logger.info(f"Cleaned up old temp file: {fname}", extra={'server': 'SYSTEM'})
            except Exception as e:
                logger.warning(f"Could not remove {fname}: {e}", extra={'server': 'SYSTEM'})


def print_summary(results):
    """Print summary of all server operations."""
    logger.info("=" * 70, extra={'server': 'SUMMARY'})
    logger.info("CDR Collection Summary", extra={'server': 'SUMMARY'})
    logger.info("=" * 70, extra={'server': 'SUMMARY'})
    
    total_downloaded = 0
    failed_servers = []
    
    for result in results:
        if result['status'] == 'success':
            logger.info(
                f"{result['server']}: Downloaded {result['downloaded']} files "
                f"(Total tracked: {result['total_tracked']})",
                extra={'server': 'SUMMARY'}
            )
            total_downloaded += result['downloaded']
        else:
            logger.error(
                f"{result['server']}: FAILED - {result.get('error', 'Unknown error')}",
                extra={'server': 'SUMMARY'}
            )
            failed_servers.append(result['server'])
    
    logger.info("-" * 70, extra={'server': 'SUMMARY'})
    logger.info(f"Total files downloaded: {total_downloaded}", extra={'server': 'SUMMARY'})
    
    if failed_servers:
        logger.warning(f"Failed servers: {', '.join(failed_servers)}", extra={'server': 'SUMMARY'})
    
    logger.info("=" * 70, extra={'server': 'SUMMARY'})


def main():
    """Main execution function."""
    try:
        # Ensure tmp directory exists with proper permissions
        ensure_directory_with_permissions(GLOBAL_CONFIG['tmp_dir'])
        
        # Process each server serially
        results = []
        for server_name, server_config in SERVERS.items():
            result = process_server(server_name, server_config)
            results.append(result)
        
        # Print summary
        print_summary(results)
        
        # Optional: cleanup temporary files from old script
        cleanup_old_tmp_files()
        
        # Return error code if any server failed
        if any(r['status'] == 'failed' for r in results):
            return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"Script execution failed: {e}", extra={'server': 'SYSTEM'})
        return 1


if __name__ == '__main__':
    exit(main())