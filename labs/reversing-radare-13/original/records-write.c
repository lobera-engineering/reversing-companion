#include <stdio.h> 
#include <stdlib.h> 
#include <string.h> 
#include <fcntl.h>
#include <stdlib.h>

  struct person  
{ 
    int id; 
    char fname[20]; 
    char lname[20]; 
}; 
  
int main () 
{ 
    int outfile;
      
    outfile = open ("person.dat", O_WRONLY | O_CREAT, 0644); 

    if(outfile > 0){
  
    struct person input1 = {1, "artik", "blue"}; 

    struct person input2 = {2, "john", "doe"}; 
      
    write (outfile , &input2, sizeof(struct person)); 
    write (outfile , &input1, sizeof(struct person)); 
  
    close(outfile); 

    }
  
    return 0; 
}
