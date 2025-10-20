#!/usr/bin/env python3

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .retention_rules import DocumentProcessor, DocumentType, DocumentAction

class IRSDocumentManager:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.processor = DocumentProcessor()
        
        # Create necessary directories
        self.dirs = {
            'inbox': self.base_dir / 'inbox',
            'to_scan': self.base_dir / 'to_scan',
            'to_shred': self.base_dir / 'to_shred',
            'to_keep': self.base_dir / 'to_keep',
            'archive': self.base_dir / 'archive'
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)

    def process_document(self, 
                        file_path: str, 
                        document_type: DocumentType,
                        document_date: datetime = None) -> Dict:
        """
        Process a single IRS document according to retention rules.
        """
        if document_date is None:
            document_date = datetime.now()

        # Get retention rule
        rule = self.processor.get_retention_rule(document_type)
        
        # Calculate retention end date
        retention_end = self.processor.calculate_retention_date(
            document_type, 
            document_date
        )

        # Determine action
        action = self.processor.get_action(document_type, document_date)

        # Process based on action
        if action == DocumentAction.SHRED:
            dest_dir = self.dirs['to_shred']
        elif action == DocumentAction.KEEP:
            dest_dir = self.dirs['to_keep']
        else:  # ARCHIVE
            dest_dir = self.dirs['archive']

        # Move file to appropriate directory
        file_name = Path(file_path).name
        new_path = dest_dir / file_name
        shutil.copy2(file_path, new_path)

        return {
            'document_type': document_type.value,
            'original_path': file_path,
            'new_path': str(new_path),
            'action': action.value,
            'retention_end': retention_end.isoformat(),
            'requires_scanning': rule.requires_scanning,
            'requires_approval': rule.requires_approval,
            'notes': rule.notes
        }

    def bulk_process(self, document_list: List[Dict]) -> List[Dict]:
        """
        Process multiple documents in bulk.
        
        document_list: List of dictionaries containing:
            - file_path: str
            - document_type: DocumentType
            - document_date: datetime (optional)
        """
        results = []
        for doc in document_list:
            try:
                result = self.process_document(
                    doc['file_path'],
                    doc['document_type'],
                    doc.get('document_date')
                )
                results.append({
                    'status': 'success',
                    'file_path': doc['file_path'],
                    'result': result
                })
            except Exception as e:
                results.append({
                    'status': 'error',
                    'file_path': doc['file_path'],
                    'error': str(e)
                })
        return results

    def generate_retention_report(self) -> List[Dict]:
        """
        Generate a report of all documents and their retention status.
        """
        report = []
        for action_dir in self.dirs.values():
            for file_path in action_dir.glob('*.*'):
                try:
                    # You might want to store metadata with files
                    # For now, we'll use basic file stats
                    stats = file_path.stat()
                    report.append({
                        'file_path': str(file_path),
                        'location': action_dir.name,
                        'created_date': datetime.fromtimestamp(stats.st_ctime),
                        'modified_date': datetime.fromtimestamp(stats.st_mtime),
                        'size': stats.st_size
                    })
                except Exception as e:
                    report.append({
                        'file_path': str(file_path),
                        'error': str(e)
                    })
        return report