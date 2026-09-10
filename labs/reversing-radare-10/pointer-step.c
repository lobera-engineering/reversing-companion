#include <string.h>
#include <stdio.h>
#include <stdlib.h>
 
main() {

int * ipoint;


  ipoint  = (int *) malloc (sizeof(int));
  *ipoint = 3;
  
  
  printf ("%p \n",ipoint);


  printf ("%i\n",*ipoint);  
  
  ipoint ++;
  
  printf ("%p\n",ipoint);
 

  printf ("%i\n",*ipoint); 
  getchar();
}
