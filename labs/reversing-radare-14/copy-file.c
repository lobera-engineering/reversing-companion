#include <stdio.h>
#include <stdlib.h>
#include <windows.h>
int main()
{
    printf("Copying file using 'CopyFile'");
    int b = CopyFile("C:\\samples\\newfile.txt","C:\\samples\\newfile2.txt",0);
    if (!b) {
        int err =  GetLastError();
        printf("Error: %d",err);
    } else {
        printf("File copied\n");
    }
    return 0;
}
