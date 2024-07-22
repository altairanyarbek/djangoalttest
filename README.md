Objective:
Create a Python function that takes a path to a folder and returns a dictionary where the keys are file types (extensions) and the values are lists of files with their full paths.

Task Description:
You need to write a function categorize_files_by_type which:

Takes a single argument, folder_path, which is a string representing the path to the root folder.
Recursively scans all subfolders and files within the given folder_path.
Categorizes all files based on their file extensions.
Returns a dictionary where the keys are file extensions (e.g., .txt, .pdf, .jpg) and the values are lists of full paths to the files with those extensions.


def categorize_files_by_type(folder_path):
    # Your implementation here
    pass

# Example usage:
result = categorize_files_by_type("/path/to/root/folder")
print(result)

# Expected output (format):
# {
#   '.txt': ['/path/to/root/folder/file1.txt', '/path/to/root/folder/subfolder/file2.txt'],
#   '.jpg': ['/path/to/root/folder/image1.jpg', '/path/to/root/folder/subfolder/image2.jpg'],
#   '.pdf': ['/path/to/root/folder/document1.pdf']
# }


Requirements:
- The function should handle any depth of nested folders.
- If a file does not have an extension, it should be categorized under the key '' (empty string).
- The solution should handle large directories efficiently.
- Provide appropriate error handling for cases where the folder_path does not exist or is not a directory.

Bonus Points:
- Write tests using unittest or pytest to validate the function's correctness.
- Implement the solution in a way that minimizes the memory footprint.
- Add optional parameters to the function to filter files by certain criteria (e.g., file size, last modified date).
- Implement logging to keep track of the function’s progress, especially for large directories.


Submission:
Submit a single Python file with the implementation and any necessary comments to explain your code. 
If you include tests, ensure they are in the same file or provide instructions on how to run them.
Upload your solution to Github, send link to that GitHub and your CV in PDF document to email: ceo@pythonrpa.org
