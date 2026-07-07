import asyncio
from app.agent.workflow import run_agent

def main():
    print("========================================")
    print(" Starting Job Tracker Automation...")
    print("========================================")
    
    try:
        # Run the abstracted agent
        result = asyncio.run(run_agent())
        
        # Extract the final_output array for a nice summary
        updates = result.get("final_output", [])
        
        print("\n========================================")
        if updates:
            print(f"✅ Success! Processed {len(updates)} job updates.")
        else:
            print("✅ Success! No new job updates found.")
        print("========================================")
            
    except Exception as e:
        print("\n❌ Automation Failed!")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
