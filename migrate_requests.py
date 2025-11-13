#!/usr/bin/env python3
"""
Migrate old JSONL request files to new standardized format

Old formats:
  Reranker: {"type": "with_headers", "sitekey": "...", "payload": {...}}
  NER:      {"type": "ner_get", "sitekey": "...", "query_params": {...}}
  QCS:      {"type": "qcs_get", "sitekey": "...", "query_params": {...}}

New format:
  GET:      {"type": "get", "sitekey": "...", "query_string": "?...", "path": "..."}
  POST:     {"type": "post", "sitekey": "...", "payload": {...}}

Usage:
  python3 migrate_requests.py -i old_requests.jsonl -o new_requests.jsonl
  python3 migrate_requests.py -d ./ner-logs --service ner
"""
import json
import argparse
from pathlib import Path
from urllib.parse import urlencode


def query_params_to_string(query_params):
    """Convert query params dict to query string."""
    if not query_params:
        return ""
    
    # Handle both dict and already-string formats
    if isinstance(query_params, str):
        return query_params if query_params.startswith('?') else '?' + query_params
    
    # Convert dict to query string
    query_string = urlencode(query_params, doseq=True)
    return '?' + query_string if query_string else ""


def migrate_entry(entry):
    """Migrate a single entry to new format."""
    old_type = entry.get("type", "")
    
    # Already in new format
    if old_type in ["get", "post"]:
        return entry
    
    # Handle entries with NO type field (old Go reranker logs)
    if not old_type:
        # Infer type from content
        if "payload" in entry:
            entry["type"] = "post"
        elif "query_string" in entry:
            entry["type"] = "get"
        else:
            print(f"⚠️  Warning: Cannot infer type for entry (no type, payload, or query_string): {entry.get('sitekey', 'unknown')}")
        return entry
    
    # Reranker: "with_headers" -> "get" or "post"
    if old_type == "with_headers":
        if "query_string" in entry:
            # Already has query_string, just update type
            entry["type"] = "get"
        elif "payload" in entry:
            # POST request
            entry["type"] = "post"
        else:
            print(f"⚠️  Warning: Unknown reranker entry format: {entry}")
        return entry
    
    # NER: "ner_get" -> "get"
    if old_type == "ner_get":
        entry["type"] = "get"
        
        # Convert query_params to query_string if exists
        if "query_params" in entry:
            entry["query_string"] = query_params_to_string(entry["query_params"])
            # Keep query_params for now, can be removed later
        
        return entry
    
    # QCS: "qcs_get" -> "get"
    if old_type == "qcs_get":
        entry["type"] = "get"
        
        # Convert query_params to query_string if exists
        if "query_params" in entry:
            entry["query_string"] = query_params_to_string(entry["query_params"])
            # Keep query_params for now, can be removed later
        
        return entry
    
    # Unknown type, return as-is with warning
    print(f"⚠️  Warning: Unknown entry type '{old_type}': {entry}")
    return entry


def migrate_file(input_file, output_file, remove_query_params=False):
    """Migrate a single JSONL file."""
    migrated_count = 0
    skipped_count = 0
    
    with open(input_file, "r") as infile, open(output_file, "w") as outfile:
        for line_num, line in enumerate(infile, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                entry = json.loads(line)
                migrated_entry = migrate_entry(entry)
                
                # Optionally remove query_params after migration
                if remove_query_params and "query_params" in migrated_entry:
                    del migrated_entry["query_params"]
                
                json.dump(migrated_entry, outfile)
                outfile.write("\n")
                migrated_count += 1
                
            except json.JSONDecodeError as e:
                print(f"⚠️  Error parsing line {line_num}: {e}")
                skipped_count += 1
                continue
    
    return migrated_count, skipped_count


def migrate_directory(directory, service=None, output_suffix="_migrated", remove_query_params=False):
    """Migrate all JSONL files in a directory."""
    directory = Path(directory)
    
    if not directory.exists():
        print(f"❌ Directory not found: {directory}")
        return
    
    # Find all JSONL files
    jsonl_files = list(directory.glob("*.jsonl"))
    
    if not jsonl_files:
        print(f"⚠️  No .jsonl files found in {directory}")
        return
    
    print(f"📂 Found {len(jsonl_files)} JSONL files in {directory}")
    print()
    
    total_migrated = 0
    total_skipped = 0
    
    for jsonl_file in jsonl_files:
        # Skip already migrated files
        if output_suffix in jsonl_file.stem:
            continue
        
        # Generate output filename
        output_file = jsonl_file.parent / f"{jsonl_file.stem}{output_suffix}.jsonl"
        
        print(f"🔄 Migrating: {jsonl_file.name}")
        migrated_count, skipped_count = migrate_file(jsonl_file, output_file, remove_query_params)
        
        print(f"   ✅ Migrated {migrated_count} entries to {output_file.name}")
        if skipped_count > 0:
            print(f"   ⚠️  Skipped {skipped_count} malformed entries")
        print()
        
        total_migrated += migrated_count
        total_skipped += skipped_count
    
    print(f"📊 Total: {total_migrated} entries migrated, {total_skipped} skipped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Migrate old JSONL request files to new standardized format"
    )
    
    # Single file mode
    parser.add_argument(
        "-i", "--input",
        help="Input JSONL file to migrate"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output JSONL file (required with --input)"
    )
    
    # Directory mode
    parser.add_argument(
        "-d", "--directory",
        help="Directory containing JSONL files to migrate"
    )
    parser.add_argument(
        "--service",
        choices=["reranker", "ner", "qcs"],
        help="Service type (for logging purposes)"
    )
    parser.add_argument(
        "--suffix",
        default="_migrated",
        help="Suffix to add to migrated files (default: _migrated)"
    )
    
    # Options
    parser.add_argument(
        "--remove-query-params",
        action="store_true",
        help="Remove query_params field after converting to query_string"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.input and args.directory:
        print("❌ Error: Cannot specify both --input and --directory")
        exit(1)
    
    if not args.input and not args.directory:
        print("❌ Error: Must specify either --input or --directory")
        parser.print_help()
        exit(1)
    
    if args.input and not args.output:
        print("❌ Error: --output is required when using --input")
        exit(1)
    
    # Single file mode
    if args.input:
        print(f"🔄 Migrating file: {args.input}")
        migrated_count, skipped_count = migrate_file(
            args.input, 
            args.output, 
            args.remove_query_params
        )
        print(f"✅ Migrated {migrated_count} entries to {args.output}")
        if skipped_count > 0:
            print(f"⚠️  Skipped {skipped_count} malformed entries")
    
    # Directory mode
    elif args.directory:
        if args.service:
            print(f"🔧 Service: {args.service}")
        migrate_directory(
            args.directory,
            args.service,
            args.suffix,
            args.remove_query_params
        )

