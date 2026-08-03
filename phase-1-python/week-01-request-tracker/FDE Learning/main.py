import json
from pathlib import Path
import re


def main():
    ID_PATTERN = re.compile(r"REQ-(\d{3})$")
    request = load_requests()
    
    while True:
        print("\n1. Add  2. List  3. View  4. Change status  5. Close  6. Open high-priority  7. Exit")
        choice = input("Enter your choice: ")
        if choice == '1':
            new_request = prompt_user(request)
            request.append(new_request)
            print("Request added successfully")
            save_requests(request)  # Save the updated requests to the file
        elif choice == '2':
            list_requests(request, status="open")
        elif choice == '3':
            r = find_requests(request, input("Enter request ID to view: "))
            print( r if r else "Request not found.")
        elif choice == '4':
            change_request_status(request, input("Enter request ID to change status: "), input("Enter new status (open/closed): "))
        elif choice == '5':
            close_request(request, input("Enter request ID to close: "))
        elif choice == '6':
            open_high_priority_requests(request)
        elif choice == '7':
            print("Exiting...")
            break
    
        
def load_requests() -> list[dict]:
    DATA_FILE = Path("data/requests.json")
    if not DATA_FILE.exists():
        return []
    try:
        with DATA_FILE.open() as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: {DATA_FILE} is not valid JSON: {e}")
        print("Fix the file or delete it to start fresh.")
        raise SystemExit(1)
requests = load_requests()

def next_request_id(existing_ids: list[dict]) -> str:
    """Find the highest numeric suffix and increment it to generate the next request ID."""
    nums =[]
    for req in existing_ids:
        match = ID_PATTERN.match(req["id"])
        if match:
            nums.append(int(match.group(1)))
    next_num = max(nums, default=0) + 1
    return f"REQ-{next_num:03d}"

def change_request_status(request_list, request_id: str, new_status: str) -> bool:
    """Changes the status of the request with the given ID and returns True if successful, False otherwise."""
    for req in request_list:
        if req["id"] == request_id:
            req["status"] = new_status
            save_requests(request_list)  # Save the updated requests to the file
            return True
    return False


def find_requests(request_list,request_id:str) -> dict | None:
    """Returns the matching request or None if not found.""";
    for req in request_list:
        if req["id"] == request_id:
            return req
        return None

def close_request(request_list, request_id: str) -> bool:
    """Closes the request with the given ID and returns True if successful, False otherwise."""
    for req in request_list:
        if req["id"] == request_id:
            req["status"] = "closed"
            save_requests(request_list)  # Save the updated requests to the file
            return True
    return False

def prompt_user(requests: list[dict]) -> dict:
    return {
        "id": next_request_id(requests),
        "customer_name": input("Enter customer name: "),
        "title": input("Enter request title: "),
        "description": input("Enter request description: "),
        "priority": input("Enter request priority (low, medium, high): "),
        "status": "open",
        "created_at": input("Enter creation date (YYYY-MM-DDTHH:MM:SSZ): "),
        "updated_at": input("Enter last updated date (YYYY-MM-DDTHH:MM:SSZ): ")
    }

def list_requests(requests: list[dict],status: str | None, priority: str | None = None) -> None:
    """Prints a summary of all requests."""

    result = requests
    if status is not None:
        result = [req for req in result if req['status'] == status]
    if priority is not None:
        result = [req for req in result if req['priority'] == priority]
    for req in result:
        print(f"ID: {req['id']}, Title: {req['title']}, Status: {req['status']}, Priority: {req['priority']}")
    if not result:
        print("No requests found matching the criteria.")

def open_high_priority_requests(requests):
    """Prints a summary of all open high-priority requests."""
    high_priority_requests = [req for req in requests if req['status'] == 'open' and req['priority'] == 'high']
    for req in high_priority_requests:
        print(f"ID: {req['id']}, Title: {req['title']}, Status: {req['status']}, Priority: {req['priority']}")
    if not high_priority_requests:
        print("No open high-priority requests found.")


DATA_FILE = Path("data/requests.json")

def save_requests(requests: list[dict]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w") as f:
        json.dump(requests, f, indent=2)

# Call after every add/update/close:
# save_requests(requests)

if __name__ == "__main__":
    main()
    
