#include <windows.h>
#include <stdio.h>

int main(void)

{
    DWORD at;

    HANDLE hFile;
    LPCWSTR fname = "C:\\samples\\newfile.txt";
    DWORD lpdwFlags[100];
    BOOL test;

    hFile = CreateFile(fname, GENERIC_WRITE,FILE_SHARE_WRITE,NULL,CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL |FILE_ATTRIBUTE_ARCHIVE | SECURITY_IMPERSONATION,NULL);

    if(hFile == INVALID_HANDLE_VALUE)
        printf("Could not open %s file, error %d\n", fname, GetLastError());
    else{
        printf("File's HANDLE is OK!\n");
        printf("f handle = %d \n", hFile);
        char arr[20] = "SAMPLESAMPLESAMPLETEXT";
        printf("%s \n", arr);
        WriteFile(hFile, &arr, 5,&at,NULL);
        printf("Bytes written: %d \n", at);
        CloseHandle(hFile);
    }

return 0;
}
