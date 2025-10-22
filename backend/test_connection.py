"""Quick test script to verify NiFi API connectivity."""

import asyncio
import sys
from app.services.nifi_client import NiFiClient


async def test_connection():
    """Test connection to NiFi API."""
    print("Testing NiFi API connection...")
    print(f"URL: http://18.235.156.98:9090/nifi-api/")
    print()
    
    client = NiFiClient()
    
    # Test health check
    print("1. Testing health check...")
    health = await client.health_check()
    if health["available"]:
        print("✓ Health check passed!")
        print(f"  NiFi version: {health.get('data', {}).get('about', {}).get('version', 'Unknown')}")
    else:
        print(f"✗ Health check failed: {health.get('error')}")
        return False
    
    print()
    
    # Test getting root process group
    print("2. Getting root process group ID...")
    try:
        root_id = await client.get_root_process_group_id()
        print(f"✓ Root process group ID: {root_id}")
    except Exception as e:
        print(f"✗ Failed to get root process group: {e}")
        return False
    
    print()
    
    # Test getting process group hierarchy
    print("3. Fetching process group hierarchy...")
    try:
        hierarchy = await client.get_process_group_hierarchy(root_id, max_depth=2)
        print(f"✓ Successfully fetched hierarchy!")
        print(f"  Root: {hierarchy.name}")
        print(f"  Children: {len(hierarchy.children)}")
        
        if hierarchy.children:
            print(f"  Child groups:")
            for child in hierarchy.children[:5]:  # Show first 5
                print(f"    - {child.name} (ID: {child.id})")
            if len(hierarchy.children) > 5:
                print(f"    ... and {len(hierarchy.children) - 5} more")
    except Exception as e:
        print(f"✗ Failed to fetch hierarchy: {e}")
        return False
    
    print()
    
    # Test getting flow status
    print("4. Getting flow status...")
    try:
        status = await client.get_flow_status()
        print(f"✓ Flow status retrieved!")
        print(f"  Active threads: {status.active_thread_count}")
        print(f"  Queued: {status.queued_count}")
        print(f"  FlowFiles received: {status.flowfiles_received}")
    except Exception as e:
        print(f"✗ Failed to get flow status: {e}")
        return False
    
    print()
    print("=" * 60)
    print("All tests passed! ✓")
    return True


if __name__ == "__main__":
    result = asyncio.run(test_connection())
    sys.exit(0 if result else 1)

