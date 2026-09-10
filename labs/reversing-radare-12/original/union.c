#include <stdio.h>


int main() {
    
union {
   char ichar; /* 1 byte */
   int num; /* 4 bytes */
} sample;

   int n1, n2;
    
    printf("Size of 'sample' union = %d \n", sizeof(sample));
    sample.num = 25;
    sample.ichar = 50;
    printf("%d", sample.num);
    

   getchar();
   getchar();
   return 0;
}
