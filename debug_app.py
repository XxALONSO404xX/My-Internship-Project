import traceback
import sys

try:
    import main
    # Just import the module to see if imports work without running the server
    print("\n\n==== SUCCESS ====")
    print("Main module imported successfully without errors.")
    print("This confirms that circular import issues have been resolved.")
    print("==== END SUCCESS ====\n")
except Exception as e:
    print("\n\n==== ERROR DETAILS ====")
    print(f"Error type: {type(e).__name__}")
    print(f"Error message: {str(e)}")
    print("\nFull traceback:")
    traceback.print_exc()
    print("==== END ERROR DETAILS ====\n")
