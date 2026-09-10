#include <string.h>
#include <stdio.h>
#include <stdlib.h>
 
main() {

int * spoint;


  spoint  = (int *) malloc (sizeof(int));
  *spoint = 3;
  
  
  printf ("%p \n",spoint);
  
  printf ("%d\n",*spoint);
  
  (*spoint) ++;
  
  printf ("%d\n",*spoint);

  
  getchar();
}
