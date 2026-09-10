#include <string.h>
#include <stdlib.h>
#include <stdio.h>
 
main() {
   int data[10];
   int i;
 
     printf ("%p\n", data);
   
    *(data)= 20;
    
     printf ("%d ", *(data));

     *(data+1)= 40;
    
     printf ("%d ", data[1]);
     getchar();
}
