#include <string.h>
#include <stdlib.h>
#include <stdio.h>
 
void x2(int *x) {
   *x = *x * 2;
}
 
main() {
   int n = 5;   
   printf("value= %d\n", n);
   x2(&n);
   printf("updated_value= %d\n", n);


  
  getchar();
}
