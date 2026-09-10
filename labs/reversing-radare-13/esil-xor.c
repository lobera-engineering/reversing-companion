#include <sys/sendfile.h>
#include <sys/stat.h>
#include <errno.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>


void main(){

        char a[4] = "abcd";
        char b[4] = "XYZU";


        for (int i=0; i < 4; i++){

                b[i] ^= a[i];
        }

        printf("%s \n",b);
}
