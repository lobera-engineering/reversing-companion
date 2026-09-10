#include <stdio.h>

int main () {
   FILE *fp;

   fp = fopen("fseek.txt","w+");
   fputs("This is a simple file, feel free to visit artik.blue to get fresh reversing stuff", fp);
  
   fseek( fp, 7, SEEK_SET );
   fputs(" C Programming Language", fp);
   fclose(fp);
   
   return(0);
}
