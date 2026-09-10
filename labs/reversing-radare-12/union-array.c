#include <string.h>
#include <stdio.h>


int main() {
    
union {
   char ichar; /* 1 byte */
   int num; /* 4 bytes */
   char arr[20];
} sample;

   int n1, n2;
    
    printf("Size of 'sample' union = %d \n", sizeof(sample));
    sample.num = 25;
    sample.ichar = 50;
    printf("value= %d \n", sample.num);
    strcpy(sample.arr,"hello world");
    printf("value= %s \n",sample.arr);
    sample.num = 65;
    printf("value= %s \n",sample.arr);


   getchar();
   getchar();
   return 0;
}
